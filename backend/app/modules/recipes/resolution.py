from decimal import Decimal, localcontext
from uuid import UUID

from pydantic import BaseModel, TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from app.modules.options.configuration_schemas import (
    ConfigurationResolveInput,
    OptionSelection,
    ResolvedConfiguration,
)
from app.modules.options.configuration_service import ProductConfigurationService
from app.modules.production.planning import calculate_plan
from app.modules.products.models import ProductVariant
from app.modules.recipes.action_templates import template_parts
from app.modules.recipes.exceptions import InvalidRecipeError
from app.modules.recipes.models import Recipe
from app.modules.recipes.schemas import (
    PlannedStep,
    PlanRead,
    RecipePlan,
    ResourceInput,
    ResourceRead,
    SelectionResourceInput,
    SupplyInputCreate,
)
from app.modules.recipes.service import RecipeService
from app.modules.recipes.service_schemas import Placeholder
from app.modules.supplies.schemas import PositiveQuantity


class RecipeResolveInput(ConfigurationResolveInput):
    variant_id: UUID
    quantity: PositiveQuantity


class ResolvedRecipe(BaseModel):
    configuration: ResolvedConfiguration
    variant_id: UUID
    quantity: PositiveQuantity
    plan: PlanRead
    planned_steps: list[PlannedStep]
    omitted_step_keys: list[str]


def applicable_plan(plan: PlanRead, configuration: ResolvedConfiguration) -> PlanRead:
    """Conservar orden a través de pasos omitidos, nunca sustituir suministro físico."""
    selected = {
        (selection.definition_id, value.value_id): value.quantity
        for selection in configuration.selections
        for value in selection.values
    }
    active = {
        step.key
        for step in plan.steps
        if step.when_selected is None
        or (step.when_selected.definition_id, step.when_selected.value_id) in selected
    }
    by_key = {step.key: step for step in plan.steps}
    result = plan.model_copy(deep=True)
    result.steps = [step for step in result.steps if step.key in active]
    for step in result.steps:
        if step.scale_by_selection and step.when_selected is not None:
            with localcontext() as context:
                context.prec = 60
                scaled = (
                    step.quantity_per_output
                    * selected[
                        (step.when_selected.definition_id, step.when_selected.value_id)
                    ]
                )
            try:
                step.quantity_per_output = TypeAdapter(
                    PositiveQuantity
                ).validate_python(scaled)
            except ValidationError as error:
                raise InvalidRecipeError(
                    "La demanda escalada excede precisión o rango permitido"
                ) from error
        if any(
            item.source_step_key is not None and item.source_step_key not in active
            for item in step.product_inputs
        ):
            raise InvalidRecipeError(
                f"Configuración incompleta: falta el proveedor físico de {step.key}"
            )
        pending = list(step.depends_on)
        prerequisites: set[str] = set()
        visited: set[str] = set()
        while pending:
            key = pending.pop()
            if key in visited:
                continue
            visited.add(key)
            if key in active:
                prerequisites.add(key)
            else:
                pending.extend(by_key[key].depends_on)
        step.depends_on = sorted(prerequisites)
    RecipePlan(steps=list(result.steps))
    return result


class RecipeResolutionService:
    def __init__(self, session: Session) -> None:
        self.options = ProductConfigurationService(session)
        self.recipes = RecipeService(session)

    def resolve(self, product_id: UUID, payload: RecipeResolveInput) -> ResolvedRecipe:
        with self.options.snapshot():
            return self.resolve_in_snapshot(product_id, payload)

    def resolve_recipe_in_snapshot(
        self,
        recipe: Recipe,
        variant: ProductVariant,
        target: Decimal,
        selections: list[OptionSelection],
    ) -> tuple[PlanRead, ResolvedConfiguration | None, list[str]]:
        """Resolver la receta elegida sin crear destino, tareas ni movimientos.

        El caller valida la variante y mantiene abierta la instantánea transaccional.
        Tanto producción como pruebas físicas deben usar estas mismas reglas.
        """
        if recipe.product_variant_id is None:
            resolved = self.resolve_in_snapshot(
                recipe.product_id,
                RecipeResolveInput(
                    variant_id=variant.id, quantity=target, selections=selections
                ),
            )
            return resolved.plan, resolved.configuration, resolved.omitted_step_keys
        if selections:
            raise InvalidRecipeError("Las selecciones requieren una receta base")
        stored = self.recipes.plan(recipe.id)
        if any(step.when_selected is not None for step in stored.steps):
            raise InvalidRecipeError(
                "Resolver selecciones antes de planificar esta receta"
            )
        for step in stored.steps:
            if step.is_final_output:
                if step.unit.value != variant.base_unit:
                    raise InvalidRecipeError(
                        "La unidad de salida no coincide con la variante"
                    )
                step.output_variant_id = variant.id
        RecipePlan(steps=list(stored.steps))
        return stored, None, []

    def resolve_actions(
        self, plan: PlanRead, product_id: UUID, planned: list[PlannedStep]
    ) -> None:
        """Formar etiquetas después de resolver recursos y demanda, sin recalcularla."""
        definitions = self.recipes._service_definitions(
            {
                step.service_definition_id
                for step in plan.steps
                if step.service_definition_id is not None
            }
        )
        if not definitions:
            return
        product = self.recipes.products.get_product(product_id)
        quantities = {step.key: step.required_quantity for step in planned}
        for step in plan.steps:
            if step.service_definition_id is None:
                continue
            definition = definitions[step.service_definition_id]
            template = (
                step.action_template
                if step.action_template is not None
                else definition.action_template
            )
            needed = (
                {field for _, field in template_parts(template) if field is not None}
                if template is not None
                else set()
            )
            # Decimal fijo, sin notación científica ni redondeo de presentación.
            quantity_text = format(quantities[step.key], "f")
            if "." in quantity_text:
                quantity_text = quantity_text.rstrip("0").rstrip(".")
            values: dict[Placeholder, str] = {
                "product": product.name,
                "quantity": quantity_text,
            }
            if len(step.resources) == 1:
                resource = step.resources[0]
                if isinstance(resource, ResourceRead):
                    values["piece"] = resource.label or resource.name
                    values["design"] = resource.name
            for key, value in values.items():
                if key in needed and key not in step.action_context:
                    step.action_context[key] = value
            details = self.recipes._service_details(step, definitions)
            step.service_name = details["service_name"]
            step.service_action = details["service_action"]
            step.service_instructions = details["service_instructions"]

    def resolve_supplies(
        self, plan: PlanRead, configuration: ResolvedConfiguration
    ) -> None:
        selections = {
            item.definition_id: item.values for item in configuration.selections
        }
        for step in plan.steps:
            used = {item.supply_id for item in step.supply_inputs}
            for requirement in step.selected_supply_inputs:
                values = selections.get(requirement.definition_id, [])
                if len(values) != 1:
                    raise InvalidRecipeError(
                        "El material requiere una única opción seleccionada"
                    )
                value = values[0]
                if value.supply_id is None:
                    raise InvalidRecipeError(
                        "La opción de material no tiene insumo vinculado"
                    )
                if value.supply_unit != requirement.unit.value:
                    raise InvalidRecipeError(
                        "La unidad del material no coincide con la cantidad por lote"
                    )
                if value.supply_id in used:
                    raise InvalidRecipeError(
                        "El material resuelto duplica un insumo del paso"
                    )
                used.add(value.supply_id)
                step.supply_inputs.append(
                    SupplyInputCreate(
                        supply_id=value.supply_id,
                        quantity_per_batch=requirement.quantity_per_batch,
                    )
                )
            step.selected_supply_inputs = []

    def resolve_resources(
        self, plan: PlanRead, configuration: ResolvedConfiguration
    ) -> None:
        selected = {
            (selection.definition_id, value.value_id): value
            for selection in configuration.selections
            for value in selection.values
        }
        revisions = self.recipes._resource_revisions(
            {
                value.revision_id
                for value in selected.values()
                if value.revision_id is not None
            }
        )
        for step in plan.steps:
            for index, resource in enumerate(step.resources):
                if not isinstance(resource, SelectionResourceInput):
                    continue
                source = resource.from_selection
                value = selected.get((source.definition_id, source.value_id))
                if value is None or value.revision_id is None:
                    raise InvalidRecipeError(
                        f"El recurso {step.key}/{resource.key} requiere "
                        "una opción seleccionada con implementación física"
                    )
                step.resources[index] = self.recipes.resolved_resource(
                    ResourceInput(
                        **resource.model_dump(exclude={"from_selection"}),
                        asset_revision_id=value.revision_id,
                    ),
                    revisions[value.revision_id],
                )

    def resolve_in_snapshot(
        self, product_id: UUID, payload: RecipeResolveInput
    ) -> ResolvedRecipe:
        """Reutilizar la instantánea abierta por lectura o producción."""
        configuration = self.options.resolve_in_snapshot(product_id, payload)
        recipe = self.recipes.base(product_id)
        if not recipe.active:
            raise InvalidRecipeError("La receta está inactiva")
        variant = self.recipes.production_variant(recipe, payload.variant_id)
        if not variant.active:
            raise InvalidRecipeError("La variante está inactiva")
        if (
            variant.base_unit == "unit"
            and payload.quantity != payload.quantity.to_integral_value()
        ):
            raise InvalidRecipeError("La cantidad en unidades debe ser entera")
        stored = self.recipes.plan(recipe.id)
        self.recipes.validate_conditions(recipe, stored.steps)
        resolved = applicable_plan(stored, configuration)
        self.resolve_resources(resolved, configuration)
        self.resolve_supplies(resolved, configuration)
        for step in resolved.steps:
            if step.is_final_output:
                if step.unit.value != variant.base_unit:
                    raise InvalidRecipeError(
                        "La unidad de salida no coincide con la variante"
                    )
                step.output_variant_id = variant.id
        RecipePlan(steps=list(resolved.steps))
        planned = calculate_plan(resolved, variant.id, payload.quantity)
        self.resolve_actions(resolved, product_id, planned)
        active_keys = {step.key for step in resolved.steps}
        return ResolvedRecipe(
            configuration=configuration,
            variant_id=variant.id,
            quantity=payload.quantity,
            plan=resolved,
            planned_steps=planned,
            omitted_step_keys=sorted(
                step.key for step in stored.steps if step.key not in active_keys
            ),
        )
