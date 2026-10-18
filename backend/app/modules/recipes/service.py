from datetime import UTC, datetime
from typing import NoReturn, TypedDict
from uuid import UUID

from sqlalchemy import or_, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.modules.assets.models import Asset, AssetRevision
from app.modules.options.configuration_models import ProductOption, ProductOptionValue
from app.modules.products.exceptions import ProductNotFoundError
from app.modules.products.models import Product, ProductVariant
from app.modules.products.service import ProductService
from app.modules.recipes.action_templates import (
    ActionTemplateError,
    render_action,
    template_parts,
)
from app.modules.recipes.exceptions import InvalidRecipeError, RecipeNotFoundError
from app.modules.recipes.models import (
    Recipe,
    RecipeProductInput,
    RecipeSelectedSupplyInput,
    RecipeStep,
    RecipeStepDependency,
    RecipeStepResource,
    RecipeSupplyInput,
)
from app.modules.recipes.repository import RecipeRepository
from app.modules.recipes.schemas import (
    PlanRead,
    ProductInputCreate,
    RecipeCreate,
    RecipePlan,
    ResourceInput,
    ResourceRead,
    SelectedSupplyInput,
    SelectionCondition,
    SelectionResourceInput,
    StepCreate,
    StepRead,
    SupplyInputCreate,
)
from app.modules.recipes.service_models import ServiceDefinition
from app.modules.supplies.models import Supply


class ServiceDetails(TypedDict, total=False):
    service_name: str
    service_action: str | None
    service_instructions: str | None


class RecipeService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = RecipeRepository(session)
        self.products = ProductService(session)

    def get(self, recipe_id: UUID, *, lock: bool = False) -> Recipe:
        recipe = self.repository.get(recipe_id, lock=lock)
        if recipe is None:
            raise RecipeNotFoundError("No existe la receta")
        return recipe

    def create(self, variant_id: UUID, payload: RecipeCreate) -> Recipe:
        try:
            variant = self.products.get_variant(variant_id)
            recipe = Recipe(
                product_id=variant.product_id,
                product_variant_id=variant_id,
                **payload.model_dump(),
            )
            self.session.add(recipe)
            self.session.commit()
            return recipe
        except ProductNotFoundError:
            self.session.rollback()
            raise
        except SQLAlchemyError as error:
            self._failure(error)

    def base(self, product_id: UUID) -> Recipe:
        self.products.get_product(product_id)
        recipe = self.repository.base_for_product(product_id)
        if recipe is None:
            raise RecipeNotFoundError("El producto no tiene receta base")
        return recipe

    def create_base(self, product_id: UUID, payload: RecipeCreate) -> Recipe:
        try:
            product = self.session.scalar(
                select(Product).where(Product.id == product_id).with_for_update()
            )
            if product is None:
                raise ProductNotFoundError("No existe el producto")
            if self.repository.base_for_product(product_id) is not None:
                raise InvalidRecipeError("El producto ya tiene una receta base")
            recipe = Recipe(
                product_id=product_id, product_variant_id=None, **payload.model_dump()
            )
            self.session.add(recipe)
            self.session.commit()
            return recipe
        except (ProductNotFoundError, InvalidRecipeError):
            self.session.rollback()
            raise
        except SQLAlchemyError as error:
            self._failure(error)

    def production_variant(
        self, recipe: Recipe, variant_id: UUID | None
    ) -> ProductVariant:
        selected_id = (
            variant_id if variant_id is not None else recipe.product_variant_id
        )
        if selected_id is None:
            raise InvalidRecipeError("La receta base requiere una variante explícita")
        variant = self.products.get_variant(selected_id)
        if variant.product_id != recipe.product_id or (
            recipe.product_variant_id is not None
            and recipe.product_variant_id != selected_id
        ):
            raise InvalidRecipeError("La variante no corresponde a esta receta")
        return variant

    def update(self, recipe_id: UUID, payload: RecipeCreate) -> Recipe:
        try:
            recipe = self.get(recipe_id, lock=True)
            for key, value in payload.model_dump().items():
                setattr(recipe, key, value)
            self.session.commit()
            return recipe
        except RecipeNotFoundError:
            self.session.rollback()
            raise
        except SQLAlchemyError as error:
            self._failure(error)

    def plan(self, recipe_id: UUID) -> PlanRead:
        recipe = self.get(recipe_id)
        steps = self.repository.steps(recipe_id)
        keys = {step.id: step.key for step in steps}
        dependencies = self.repository.dependencies(recipe_id)
        supplies = self.repository.supply_inputs(recipe_id)
        selected_supplies = self.repository.selected_supply_inputs(recipe_id)
        products = self.repository.product_inputs(recipe_id)
        resources = self.repository.resources(recipe_id)
        revisions = self._resource_revisions(
            {
                item.asset_revision_id
                for item in resources
                if item.asset_revision_id is not None
            }
        )
        definitions = self._service_definitions(
            {
                step.service_definition_id
                for step in steps
                if step.service_definition_id is not None
            }
        )
        return PlanRead(
            recipe_id=recipe_id,
            steps=[
                StepRead(
                    **{
                        key: getattr(step, key)
                        for key in StepRead.model_fields
                        if key
                        not in {
                            "when_selected",
                            "depends_on",
                            "supply_inputs",
                            "selected_supply_inputs",
                            "product_inputs",
                            "resources",
                            "service_name",
                            "service_action",
                            "service_instructions",
                        }
                    },
                    **self._service_details(
                        step,
                        definitions,
                        automatic=recipe.product_variant_id is None,
                        resource_count=sum(
                            item.step_id == step.id for item in resources
                        ),
                    ),
                    when_selected=SelectionCondition(
                        definition_id=step.condition_definition_id,
                        value_id=step.condition_value_id,
                    )
                    if step.condition_definition_id is not None
                    and step.condition_value_id is not None
                    else None,
                    resources=[
                        self._resource_read(item, revisions)
                        for item in resources
                        if item.step_id == step.id
                    ],
                    selected_supply_inputs=[
                        SelectedSupplyInput.model_validate(item)
                        for item in selected_supplies
                        if item.step_id == step.id
                    ],
                    supply_inputs=[
                        SupplyInputCreate(
                            supply_id=item.supply_id,
                            quantity_per_batch=item.quantity_per_batch,
                        )
                        for item in supplies
                        if item.step_id == step.id
                    ],
                    product_inputs=[
                        ProductInputCreate(
                            product_variant_id=item.product_variant_id,
                            quantity_per_batch=item.quantity_per_batch,
                            source_step_key=keys[item.source_step_id]
                            if item.source_step_id
                            else None,
                        )
                        for item in products
                        if item.step_id == step.id
                    ],
                    depends_on=sorted(
                        keys[dep.depends_on_step_id]
                        for dep in dependencies
                        if dep.step_id == step.id
                    ),
                )
                for step in steps
            ],
        )

    def replace_plan(self, recipe_id: UUID, payload: RecipePlan) -> PlanRead:
        try:
            # Serializa modificaciones del grafo físico entre distintas recetas.
            self.session.execute(text("SELECT pg_advisory_xact_lock(900902)"))
            recipe = self.get(recipe_id, lock=True)
            final_steps = [step for step in payload.steps if step.is_final_output]
            if len(final_steps) > 1 or (
                final_steps and recipe.product_variant_id is not None
            ):
                raise InvalidRecipeError(
                    "Sólo la receta base admite una salida final parametrizada"
                )
            for step in final_steps:
                if step.output_variant_id is not None or step.quantity_per_output != 1:
                    raise InvalidRecipeError(
                        "La salida final requiere cantidad 1 y no fija variante"
                    )
            self.validate_conditions(recipe, payload.steps)
            self._validate_composition(recipe, payload)
            self._resource_revisions(
                {
                    item.asset_revision_id
                    for step in payload.steps
                    for item in step.resources
                    if isinstance(item, ResourceInput)
                }
            )
            definitions = self._service_definitions(
                {
                    step.service_definition_id
                    for step in payload.steps
                    if step.service_definition_id is not None
                },
                lock=True,
            )
            for step in payload.steps:
                if step.service_definition_id is not None:
                    if not definitions[step.service_definition_id].active:
                        raise InvalidRecipeError("El servicio está inactivo")
                    self._service_details(
                        step,
                        definitions,
                        automatic=recipe.product_variant_id is None,
                        resource_count=len(step.resources),
                    )
            supply_ids = {
                item.supply_id for step in payload.steps for item in step.supply_inputs
            }
            if supply_ids:
                self.session.scalars(
                    select(Supply)
                    .where(Supply.id.in_(supply_ids))
                    .order_by(Supply.id)
                    .with_for_update()
                ).all()
            for step in payload.steps:
                for supply_input in step.supply_inputs:
                    supply = self.session.scalar(
                        select(Supply)
                        .where(Supply.id == supply_input.supply_id)
                        .with_for_update()
                    )
                    if supply is None or not supply.active:
                        raise InvalidRecipeError("El insumo no existe o está inactivo")
                for product_input in step.product_inputs:
                    variant = self.products.get_variant(
                        product_input.product_variant_id
                    )
                    product = self.products.get_product(variant.product_id)
                    if not variant.active or not product.active:
                        raise InvalidRecipeError("El componente está inactivo")
                if step.output_variant_id:
                    variant = self.products.get_variant(step.output_variant_id)
                    if (
                        recipe.product_variant_id is None
                        and variant.product_id == recipe.product_id
                    ):
                        raise InvalidRecipeError(
                            "La salida del producto debe usar is_final_output"
                        )
                    if variant.base_unit != step.unit.value:
                        raise InvalidRecipeError(
                            "La salida y el paso deben usar la misma unidad"
                        )
            self.repository.clear_steps(recipe_id)
            steps: dict[str, RecipeStep] = {}
            for position, payload_step in enumerate(payload.steps):
                model = RecipeStep(
                    recipe_id=recipe_id,
                    position=position,
                    condition_definition_id=payload_step.when_selected.definition_id
                    if payload_step.when_selected
                    else None,
                    condition_value_id=payload_step.when_selected.value_id
                    if payload_step.when_selected
                    else None,
                    **payload_step.model_dump(
                        exclude={
                            "when_selected",
                            "depends_on",
                            "supply_inputs",
                            "selected_supply_inputs",
                            "product_inputs",
                            "resources",
                        }
                    ),
                )
                self.session.add(model)
                steps[model.key] = model
            self.session.flush()
            for payload_step in payload.steps:
                for key in payload_step.depends_on:
                    self.session.add(
                        RecipeStepDependency(
                            recipe_id=recipe_id,
                            step_id=steps[payload_step.key].id,
                            depends_on_step_id=steps[key].id,
                        )
                    )
            for payload_step in payload.steps:
                step_id = steps[payload_step.key].id
                for resource in payload_step.resources:
                    source = (
                        resource.from_selection
                        if isinstance(resource, SelectionResourceInput)
                        else None
                    )
                    self.session.add(
                        RecipeStepResource(
                            step_id=step_id,
                            selection_definition_id=source.definition_id
                            if source
                            else None,
                            selection_value_id=source.value_id if source else None,
                            **resource.model_dump(exclude={"from_selection"}),
                        )
                    )
                for selected_supply in payload_step.selected_supply_inputs:
                    self.session.add(
                        RecipeSelectedSupplyInput(
                            step_id=step_id, **selected_supply.model_dump()
                        )
                    )
                for supply_input in payload_step.supply_inputs:
                    self.session.add(
                        RecipeSupplyInput(step_id=step_id, **supply_input.model_dump())
                    )
                for product_input in payload_step.product_inputs:
                    self.session.add(
                        RecipeProductInput(
                            step_id=step_id,
                            product_variant_id=product_input.product_variant_id,
                            quantity_per_batch=product_input.quantity_per_batch,
                            source_step_id=steps[product_input.source_step_key].id
                            if product_input.source_step_key
                            else None,
                        )
                    )
            recipe.updated_at = datetime.now(UTC)
            self.session.commit()
            self.session.expire_all()
            return self.plan(recipe_id)
        except (RecipeNotFoundError, ProductNotFoundError, InvalidRecipeError):
            self.session.rollback()
            raise
        except SQLAlchemyError as error:
            self._failure(error)

    def validate_conditions(
        self, recipe: Recipe, steps: list[StepCreate] | list[StepRead]
    ) -> None:
        conditions = [
            step.when_selected for step in steps if step.when_selected is not None
        ]
        conditions.extend(
            resource.from_selection
            for step in steps
            for resource in step.resources
            if isinstance(resource, SelectionResourceInput)
        )
        material_definitions = {
            item.definition_id for step in steps for item in step.selected_supply_inputs
        }
        if material_definitions:
            allowed_definitions = set(
                self.session.scalars(
                    select(ProductOption.definition_id).where(
                        ProductOption.product_id == recipe.product_id
                    )
                )
            )
            if not material_definitions <= allowed_definitions:
                raise InvalidRecipeError(
                    "La característica de material no pertenece al producto"
                )
        if not conditions and not material_definitions:
            return
        if recipe.product_variant_id is not None:
            raise InvalidRecipeError(
                "Las condiciones requieren una receta base de producto"
            )
        allowed = set(
            self.session.execute(
                select(
                    ProductOptionValue.definition_id, ProductOptionValue.value_id
                ).where(ProductOptionValue.product_id == recipe.product_id)
            ).tuples()
        )
        if any(
            (item.definition_id, item.value_id) not in allowed for item in conditions
        ):
            raise InvalidRecipeError(
                "La condición refiere a una opción no permitida en el producto"
            )

    def _validate_composition(self, recipe: Recipe, payload: RecipePlan) -> None:
        graph: dict[UUID, set[UUID]] = {}
        rows = self.session.execute(
            select(ProductVariant.id, RecipeProductInput.product_variant_id)
            .select_from(Recipe)
            .join(
                ProductVariant,
                (ProductVariant.product_id == Recipe.product_id)
                & or_(
                    Recipe.product_variant_id.is_(None),
                    ProductVariant.id == Recipe.product_variant_id,
                ),
            )
            .join(RecipeStep, RecipeStep.recipe_id == Recipe.id)
            .join(RecipeProductInput, RecipeProductInput.step_id == RecipeStep.id)
            .where(Recipe.id != recipe.id)
        )
        for output_id, input_id in rows:
            graph.setdefault(output_id, set()).add(input_id)
        output_ids = (
            [recipe.product_variant_id]
            if recipe.product_variant_id is not None
            else list(
                self.session.scalars(
                    select(ProductVariant.id).where(
                        ProductVariant.product_id == recipe.product_id
                    )
                )
            )
        )
        for step in payload.steps:
            for item in step.product_inputs:
                for output_id in output_ids:
                    graph.setdefault(output_id, set()).add(item.product_variant_id)
                if step.output_variant_id:
                    graph.setdefault(step.output_variant_id, set()).add(
                        item.product_variant_id
                    )
        # También se incluyen las salidas intermedias de las demás recetas.
        intermediate = self.session.execute(
            select(RecipeStep.output_variant_id, RecipeProductInput.product_variant_id)
            .join(RecipeProductInput, RecipeProductInput.step_id == RecipeStep.id)
            .where(
                RecipeStep.recipe_id != recipe.id,
                RecipeStep.output_variant_id.is_not(None),
            )
        )
        for output_id, input_id in intermediate:
            graph.setdefault(output_id, set()).add(input_id)
        pending = set(graph)
        resolved: set[UUID] = {
            item for values in graph.values() for item in values if item not in graph
        }
        while pending:
            ready = {key for key in pending if graph[key] <= resolved}
            if not ready:
                raise InvalidRecipeError("La composición física contiene un ciclo")
            resolved.update(ready)
            pending.difference_update(ready)

    def _resource_read(
        self,
        item: RecipeStepResource,
        revisions: dict[UUID, tuple[AssetRevision, Asset]],
    ) -> ResourceRead | SelectionResourceInput:
        if item.asset_revision_id is None:
            if item.selection_definition_id is None or item.selection_value_id is None:
                raise InvalidRecipeError("El recurso no tiene un origen completo")
            return SelectionResourceInput(
                key=item.key,
                from_selection=SelectionCondition(
                    definition_id=item.selection_definition_id,
                    value_id=item.selection_value_id,
                ),
                quantity_per_batch=item.quantity_per_batch,
                label=item.label,
            )
        return self.resolved_resource(
            ResourceInput.model_validate(item), revisions[item.asset_revision_id]
        )

    @staticmethod
    def resolved_resource(
        item: ResourceInput, physical: tuple[AssetRevision, Asset]
    ) -> ResourceRead:
        revision, asset = physical
        return ResourceRead(
            **item.model_dump(),
            asset_id=asset.id,
            revision_number=revision.number,
            code=asset.code,
            name=asset.name,
            archived=asset.archived,
        )

    def _resource_revisions(
        self, ids: set[UUID]
    ) -> dict[UUID, tuple[AssetRevision, Asset]]:
        if not ids:
            return {}
        rows = (
            self.session.execute(
                select(AssetRevision, Asset)
                .join(Asset, Asset.id == AssetRevision.asset_id)
                .where(AssetRevision.id.in_(ids))
                .execution_options(populate_existing=True)
            )
            .tuples()
            .all()
        )
        revisions = {revision.id: (revision, asset) for revision, asset in rows}
        if revisions.keys() != ids:
            raise InvalidRecipeError("No existe una revisión de recurso referenciada")
        return revisions

    def _service_definitions(
        self, ids: set[UUID], *, lock: bool = False
    ) -> dict[UUID, ServiceDefinition]:
        if not ids:
            return {}
        query = (
            select(ServiceDefinition)
            .where(ServiceDefinition.id.in_(ids))
            .order_by(ServiceDefinition.id)
        )
        if lock:
            query = query.with_for_update()
        definitions = {
            row.id: row
            for row in self.session.scalars(
                query.execution_options(populate_existing=True)
            )
        }
        if definitions.keys() != ids:
            raise InvalidRecipeError("No existe un servicio referenciado")
        return definitions

    def _service_details(
        self,
        step: RecipeStep | StepRead | StepCreate,
        definitions: dict[UUID, ServiceDefinition],
        *,
        automatic: bool = False,
        resource_count: int = 0,
    ) -> ServiceDetails:
        if step.service_definition_id is None:
            return {}
        definition = definitions[step.service_definition_id]
        template = (
            step.action_template
            if step.action_template is not None
            else definition.action_template
        )
        values: dict[str, str] = {
            key: value for key, value in step.action_context.items()
        }
        try:
            missing = (
                {
                    field
                    for _, field in template_parts(template)
                    if field is not None and field not in values
                }
                if template is not None
                else set()
            )
            deferred = {"product", "quantity"} if automatic else set()
            if automatic and resource_count == 1:
                deferred.update({"piece", "design"})
            if automatic and resource_count > 1 and missing & {"piece", "design"}:
                raise ActionTemplateError(
                    "Contexto de servicio ambiguo: indicar piece/design explícitos "
                    "cuando el paso tiene varios recursos"
                )
            action = (
                None
                if missing and missing <= deferred
                else (
                    render_action(template, values)
                    if template is not None
                    else definition.name
                )
            )
        except ActionTemplateError as error:
            raise InvalidRecipeError(str(error)) from error
        return {
            "service_name": definition.name,
            "service_action": action,
            "service_instructions": definition.instructions,
        }

    def _failure(self, error: SQLAlchemyError) -> NoReturn:
        self.session.rollback()
        raise PersistenceError("No se pudo guardar la receta") from error
