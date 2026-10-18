from datetime import UTC, datetime
from decimal import Decimal
from typing import NoReturn
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.modules.machines.models import Machine
from app.modules.options.configuration_schemas import (
    OptionSelection,
    ResolvedConfiguration,
)
from app.modules.options.configuration_service import ProductConfigurationService
from app.modules.options.exceptions import OptionConflictError, OptionNotFoundError
from app.modules.production.models import (
    ProductionTask,
    ProductionTaskAssetRevision,
    ProductionTaskDependency,
)
from app.modules.production.plan_models import ProductionPlan
from app.modules.production.plan_schemas import (
    ProductionPlanCreate,
    ProductionPlanRead,
    ProductionPreview,
)
from app.modules.production.planning import calculate_plan, quantity
from app.modules.production.repository import ProductionTaskRepository
from app.modules.production.schemas import ProductionTaskRead
from app.modules.products.allocation_models import ProductStockAllocation
from app.modules.products.allocation_schemas import AllocationCreate
from app.modules.products.allocation_service import ProductAllocationService
from app.modules.products.exceptions import ProductNotFoundError
from app.modules.products.models import Product, ProductVariant
from app.modules.products.stock_service import (
    ProductStockConflictError,
    ProductStockService,
)
from app.modules.recipes.exceptions import InvalidRecipeError, RecipeNotFoundError
from app.modules.recipes.models import Recipe
from app.modules.recipes.resolution import RecipeResolutionService
from app.modules.recipes.schemas import PlanRead, ResourceRead
from app.modules.recipes.service import RecipeService
from app.modules.recipes.types import RecipeStepKind
from app.modules.supplies.models import Supply
from app.modules.supplies.reservation_models import SupplyReservation
from app.modules.supplies.reservation_service import SupplyReservationService


class ProductionPlanService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.recipes = RecipeService(session)

    def get(self, plan_id: UUID) -> ProductionPlan:
        plan = self.session.get(ProductionPlan, plan_id)
        if plan is None:
            raise ProductNotFoundError("No existe el plan de producción")
        return plan

    def read(self, plan: ProductionPlan) -> ProductionPlanRead:
        tasks = list(
            self.session.scalars(
                select(ProductionTask)
                .where(ProductionTask.production_plan_id == plan.id)
                .order_by(ProductionTask.queue_position, ProductionTask.id)
            )
        )
        warnings = []
        # Disponibilidad actual, no un hecho histórico del plan.
        supply_ids = sorted(
            {
                item["supply_id"]
                for task in tasks
                for item in (task.recipe_snapshot or {})
                .get("step", {})
                .get("supply_inputs", [])
            }
        )
        for supply_id in supply_ids:
            if (
                SupplyReservationService(self.session)
                .availability(UUID(supply_id))
                .shortage_warning
            ):
                warnings.append("insufficient_supply_stock:" + supply_id)
        if ProductStockService(self.session).stock(plan.variant_id).shortage_warning:
            warnings.append("insufficient_product_stock:" + str(plan.variant_id))
        return ProductionPlanRead(
            **{
                field: getattr(plan, field)
                for field in ProductionPlanRead.model_fields
                if field not in {"tasks", "warnings"}
            },
            tasks=[ProductionTaskRead.model_validate(task) for task in tasks],
            warnings=warnings,
        )

    def _resolve_recipe(
        self,
        recipe: Recipe,
        variant: ProductVariant,
        target: Decimal,
        selections: list[OptionSelection],
    ) -> tuple[PlanRead, ResolvedConfiguration | None, list[str]]:
        return RecipeResolutionService(self.session).resolve_recipe_in_snapshot(
            recipe, variant, target, selections
        )

    def preview(
        self,
        recipe_id: UUID,
        target: Decimal,
        variant_id: UUID | None = None,
        selections: list[OptionSelection] | None = None,
    ) -> ProductionPreview:
        with ProductConfigurationService(self.session).snapshot():
            recipe = self.recipes.get(recipe_id)
            variant = self.recipes.production_variant(recipe, variant_id)
            plan, configuration, omitted = self._resolve_recipe(
                recipe, variant, target, selections or []
            )
            return ProductionPreview(
                recipe_id=recipe_id,
                target_quantity=target,
                configuration=configuration,
                omitted_step_keys=omitted,
                steps=calculate_plan(plan, variant.id, target),
            )

    def _validate_machine_assignments(
        self, recipe: PlanRead, assignments: dict[str, UUID]
    ) -> None:
        by_key = {step.key: step for step in recipe.steps}
        if assignments.keys() - by_key.keys():
            raise InvalidRecipeError("La asignación refiere a un paso inexistente")
        machine_ids = set(assignments.values())
        if not machine_ids:
            return
        machines = {
            machine.id: machine
            for machine in self.session.scalars(
                select(Machine)
                .where(Machine.id.in_(machine_ids))
                .order_by(Machine.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        }
        if machines.keys() != machine_ids or any(
            not machine.active for machine in machines.values()
        ):
            raise InvalidRecipeError("La máquina asignada no existe o está inactiva")
        for key, machine_id in assignments.items():
            step = by_key[key]
            if step.kind in {RecipeStepKind.SERVICE, RecipeStepKind.WAIT}:
                raise InvalidRecipeError("Service y wait no asignan máquina")
            if (
                step.required_machine_type is not None
                and machines[machine_id].machine_type
                != step.required_machine_type.value
            ):
                raise InvalidRecipeError("La máquina asignada no cumple los requisitos")

    def create(
        self,
        payload: ProductionPlanCreate,
        *,
        order_id: UUID | None = None,
        component_id: UUID | None = None,
    ) -> ProductionPlan:
        # Entrada sin consultas previas; cada intento abre una instantánea nueva.
        for attempt in range(3):
            try:
                self.session.execute(
                    text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                )
                return self._create(
                    payload, order_id=order_id, component_id=component_id
                )
            except SQLAlchemyError as error:
                self.session.rollback()
                retryable = isinstance(error, DBAPIError) and (
                    getattr(error.orig, "sqlstate", None) in {"40001", "40P01"}
                    or (
                        getattr(error.orig, "sqlstate", None) == "23505"
                        and getattr(
                            getattr(error.orig, "diag", None), "constraint_name", None
                        )
                        == "uq_production_plans_request_id"
                    )
                )
                if retryable and attempt < 2:
                    continue
                if retryable:
                    raise ProductStockConflictError(
                        "Conflicto concurrente; reintentar la petición"
                    ) from error
                self._failure(error)
        raise AssertionError("Bucle de reintentos agotado")

    def _create(
        self,
        payload: ProductionPlanCreate,
        *,
        order_id: UUID | None = None,
        component_id: UUID | None = None,
    ) -> ProductionPlan:
        try:
            destinations = ProductAllocationService(self.session)
            destinations.validate_destination(
                order_id, component_id, require_active=False
            )
            original = self.session.scalar(
                select(ProductionPlan).where(
                    ProductionPlan.request_id == payload.request_id
                )
            )
            if original is not None:
                if (
                    original.order_id != order_id
                    or original.project_component_id != component_id
                    or ProductionPlanCreate.model_validate(original.request_payload)
                    != payload
                ):
                    raise ProductStockConflictError(
                        "La petición corresponde a otro plan"
                    )
                return original
            destinations.validate_destination(order_id, component_id)
            recipe = self.recipes.get(payload.recipe_id, lock=True)
            if not recipe.active:
                raise InvalidRecipeError("La receta está inactiva")
            selected_variant = self.recipes.production_variant(
                recipe, payload.variant_id
            )
            variant_id = selected_variant.id
            recipe_plan, configuration, omitted = self._resolve_recipe(
                recipe, selected_variant, payload.target_quantity, payload.selections
            )
            calculated = calculate_plan(
                recipe_plan, variant_id, payload.target_quantity
            )
            by_key = {step.key: step for step in recipe_plan.steps}
            supply_ids = {
                item.supply_id
                for step in recipe_plan.steps
                for item in step.supply_inputs
            }
            supplies = (
                {
                    item.id: item
                    for item in self.session.scalars(
                        select(Supply)
                        .where(Supply.id.in_(supply_ids))
                        .order_by(Supply.id)
                        .with_for_update()
                        .execution_options(populate_existing=True)
                    )
                }
                if supply_ids
                else {}
            )
            if set(supplies) != supply_ids or any(
                not item.active for item in supplies.values()
            ):
                raise InvalidRecipeError("Un insumo no existe o está inactivo")
            variant_ids = (
                {variant_id}
                | {
                    step.output_variant_id
                    for step in recipe_plan.steps
                    if step.output_variant_id is not None
                }
                | {
                    item.product_variant_id
                    for step in recipe_plan.steps
                    for item in step.product_inputs
                }
            )
            variants = {
                item.id: item
                for item in self.session.scalars(
                    select(ProductVariant)
                    .where(ProductVariant.id.in_(variant_ids))
                    .order_by(ProductVariant.id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
            }
            if set(variants) != variant_ids or any(
                not item.active for item in variants.values()
            ):
                raise InvalidRecipeError("Una variante no existe o está inactiva")
            parents = self.session.scalars(
                select(Product).where(
                    Product.id.in_({item.product_id for item in variants.values()})
                )
            ).all()
            if any(not item.active for item in parents):
                raise InvalidRecipeError("Un producto está inactivo")
            for step in recipe_plan.steps:
                if (
                    step.output_variant_id is not None
                    and variants[step.output_variant_id].base_unit != step.unit.value
                ):
                    raise InvalidRecipeError("La unidad de salida no coincide")
            self._validate_machine_assignments(recipe_plan, payload.machine_assignments)
            allocation = None
            if payload.allocate_output:
                allocation_payload = AllocationCreate(
                    request_id=uuid4(),
                    variant_id=variant_id,
                    order_id=order_id,
                    project_component_id=component_id,
                    quantity=payload.target_quantity,
                )
                allocation = ProductStockAllocation(
                    **allocation_payload.model_dump(),
                    initial_quantity=payload.target_quantity,
                    unit=variants[variant_id].base_unit,
                    request_payload=allocation_payload.model_dump(mode="json"),
                )
                self.session.add(allocation)
                self.session.flush()
            plan = ProductionPlan(
                recipe_id=recipe.id,
                variant_id=variant_id,
                order_id=order_id,
                project_component_id=component_id,
                allocation_id=allocation.id if allocation else None,
                target_quantity=payload.target_quantity,
                request_id=payload.request_id,
                request_payload=payload.model_dump(mode="json"),
                snapshot={
                    "configuration": configuration.model_dump(mode="json")
                    if configuration
                    else None,
                    "omitted_step_keys": omitted,
                    "machine_assignments": {
                        key: str(machine_id)
                        for key, machine_id in sorted(
                            payload.machine_assignments.items()
                        )
                    },
                    "recipe_name": recipe.name,
                    "recipe": {
                        "steps": [
                            step.model_dump(mode="json", exclude={"id", "position"})
                            for step in recipe_plan.steps
                        ]
                    },
                    "planning": [item.model_dump(mode="json") for item in calculated],
                },
            )
            self.session.add(plan)
            self.session.flush()
            tasks: dict[str, ProductionTask] = {}
            repository = ProductionTaskRepository(self.session)
            for position, calculation in enumerate(calculated):
                step = by_key[calculation.key]
                task = ProductionTask(
                    code=repository.next_code(datetime.now(UTC).year),
                    production_plan_id=plan.id,
                    recipe_step_key=step.key,
                    recipe_id=recipe.id,
                    recipe_snapshot={
                        "step": step.model_dump(
                            mode="json", exclude={"id", "position"}
                        ),
                        "planning": calculation.model_dump(mode="json"),
                    },
                    origin="recipe",
                    execution_mode="runs",
                    output_variant_id=step.output_variant_id,
                    order_id=order_id,
                    project_component_id=component_id,
                    task_type=step.task_type.value,
                    title=step.title,
                    description="\n\n".join(
                        part
                        for part in (
                            step.service_action,
                            step.service_instructions,
                            step.instructions,
                        )
                        if part
                    )
                    or None,
                    planned_quantity=calculation.required_quantity,
                    planned_unit=step.unit.value,
                    machine_id=payload.machine_assignments.get(step.key),
                    queue_position=position,
                    production_parameters=step.parameters,
                )
                self.session.add(task)
                tasks[step.key] = task
            self.session.flush()
            for calculation in calculated:
                step = by_key[calculation.key]
                task = tasks[step.key]
                if any(not isinstance(item, ResourceRead) for item in step.resources):
                    raise InvalidRecipeError("El plan contiene recursos sin resolver")
                for revision_id in sorted(
                    {
                        resource.asset_revision_id
                        for resource in step.resources
                        if isinstance(resource, ResourceRead)
                    }
                ):
                    self.session.add(
                        ProductionTaskAssetRevision(
                            task_id=task.id, asset_revision_id=revision_id
                        )
                    )
                for prerequisite in step.depends_on:
                    self.session.add(
                        ProductionTaskDependency(
                            task_id=task.id, depends_on_task_id=tasks[prerequisite].id
                        )
                    )
                if payload.reserve_supplies:
                    for item in step.supply_inputs:
                        self.session.add(
                            SupplyReservation(
                                task_id=task.id,
                                supply_id=item.supply_id,
                                quantity=quantity(
                                    calculation.batches * item.quantity_per_batch
                                ),
                                unit=supplies[item.supply_id].base_unit,
                            )
                        )
            self.session.commit()
            return plan
        except (
            RecipeNotFoundError,
            OptionConflictError,
            OptionNotFoundError,
            InvalidRecipeError,
            ProductNotFoundError,
            ProductStockConflictError,
        ):
            self.session.rollback()
            raise
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def _failure(self, error: SQLAlchemyError) -> NoReturn:
        self.session.rollback()
        if isinstance(error, IntegrityError):
            raise ProductStockConflictError(
                "Conflicto concurrente de generación"
            ) from error
        raise PersistenceError("No se pudo generar el plan") from error
