from datetime import UTC, datetime
from decimal import Decimal
from typing import NoReturn
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.modules.production.plan_service import ProductionPlanService
from app.modules.production.planning import calculate_plan
from app.modules.production.run_exceptions import RunConflictError, RunNotFoundError
from app.modules.production.run_models import ProductionRun
from app.modules.production.run_schemas import RunClose, RunCreate
from app.modules.production.run_service import ProductionRunService
from app.modules.production.test_print_models import (
    TestPrint,
    TestPrintAssetRevision,
    TestPrintStep,
)
from app.modules.production.test_print_schemas import (
    TestPrintCreate,
    TestPrintPromotion,
    TestPrintRead,
    TestPrintStepRead,
)
from app.modules.products.consumption_models import ProductionRunProductConsumption
from app.modules.products.consumption_schemas import RunProductConsumptionCreate
from app.modules.products.consumption_service import RunProductConsumptionService
from app.modules.products.models import ProductVariant
from app.modules.products.stock_models import ProductStockMovement
from app.modules.products.stock_service import ProductStockService
from app.modules.recipes.resolution import RecipeResolutionService
from app.modules.recipes.schemas import ResourceRead, StepRead
from app.modules.recipes.service import RecipeService
from app.modules.supplies.consumption_service import RunSupplyConsumptionService
from app.modules.supplies.models import Supply
from app.modules.supplies.reservation_service import SupplyReservationService


class TestPrintService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, print_id: UUID, *, lock: bool = False) -> TestPrint:
        query = select(TestPrint).where(TestPrint.id == print_id)
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        result = self.session.scalar(query)
        if result is None:
            raise RunNotFoundError("No existe la prueba de receta")
        return result

    def steps(self, print_id: UUID) -> list[TestPrintStep]:
        return list(
            self.session.scalars(
                select(TestPrintStep)
                .where(TestPrintStep.test_print_id == print_id)
                .order_by(TestPrintStep.key)
            )
        )

    def totals(self, step_id: UUID) -> tuple[Decimal, Decimal]:
        good, failed = self.session.execute(
            select(
                func.coalesce(func.sum(ProductionRun.good_quantity), 0),
                func.coalesce(func.sum(ProductionRun.failed_quantity), 0),
            ).where(
                ProductionRun.test_print_step_id == step_id,
                ProductionRun.status == "closed",
            )
        ).one()
        return Decimal(good), Decimal(failed)

    def open_run(self, step_id: UUID) -> ProductionRun | None:
        return self.session.scalar(
            select(ProductionRun).where(
                ProductionRun.test_print_step_id == step_id,
                ProductionRun.status == "running",
            )
        )

    def available_internal(self, step_id: UUID) -> Decimal:
        used = self.session.scalar(
            select(
                func.coalesce(func.sum(ProductionRunProductConsumption.consumed), 0)
            ).where(ProductionRunProductConsumption.internal_source_step_id == step_id)
        )
        return self.totals(step_id)[0] - Decimal(used or 0)

    def read(self, item: TestPrint) -> TestPrintRead:
        result = []
        promotable = Decimal(0)
        for step in self.steps(item.id):
            good, failed = self.totals(step.id)
            running = self.open_run(step.id)
            if item.status == "completed" and step.output_variant_id == item.variant_id:
                promotable = self.available_internal(step.id)
            result.append(
                TestPrintStepRead(
                    id=step.id,
                    key=step.key,
                    planned_quantity=step.planned_quantity,
                    good_quantity=good,
                    failed_quantity=failed,
                    completed=good >= step.planned_quantity and running is None,
                    open_run_id=running.id if running else None,
                    snapshot=step.snapshot,
                )
            )
        movement_id = self.session.scalar(
            select(ProductStockMovement.id).where(
                ProductStockMovement.test_print_id == item.id
            )
        )
        return TestPrintRead(
            id=item.id,
            recipe_id=item.recipe_id,
            variant_id=item.variant_id,
            target_quantity=item.target_quantity,
            unit=item.unit,
            status=item.status,
            request_id=item.request_id,
            snapshot=item.snapshot,
            steps=result,
            promotion_movement_id=movement_id,
            promotable_quantity=promotable if movement_id is None else Decimal(0),
            created_at=item.created_at,
        )

    def create(self, payload: TestPrintCreate) -> TestPrint:
        for attempt in range(3):
            try:
                self.session.execute(
                    text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                )
                original = self.session.scalar(
                    select(TestPrint).where(TestPrint.request_id == payload.request_id)
                )
                if original is not None:
                    if (
                        TestPrintCreate.model_validate(original.request_payload)
                        != payload
                    ):
                        raise RunConflictError("La petición corresponde a otra prueba")
                    return original
                recipes = RecipeService(self.session)
                recipe = recipes.get(payload.recipe_id, lock=True)
                variant = recipes.production_variant(recipe, payload.variant_id)
                product = recipes.products.get_product(variant.product_id)
                if not recipe.active or not variant.active or not product.active:
                    raise RunConflictError(
                        "Receta, variante y producto deben estar activos"
                    )
                self._whole_units(payload.target_quantity, variant.base_unit)
                plan, configuration, omitted = RecipeResolutionService(
                    self.session
                ).resolve_recipe_in_snapshot(
                    recipe, variant, payload.target_quantity, payload.selections
                )
                planning = calculate_plan(plan, variant.id, payload.target_quantity)
                supply_ids = {
                    value.supply_id
                    for step in plan.steps
                    for value in step.supply_inputs
                }
                supplies = list(
                    self.session.scalars(
                        select(Supply).where(Supply.id.in_(supply_ids))
                    )
                )
                if len(supplies) != len(supply_ids) or any(
                    not supply.active for supply in supplies
                ):
                    raise RunConflictError(
                        "Un insumo requerido no existe o está inactivo"
                    )
                ProductionPlanService(self.session)._validate_machine_assignments(
                    plan, payload.machine_assignments
                )
                calculations = {step.key: step for step in planning}
                item = TestPrint(
                    recipe_id=recipe.id,
                    variant_id=variant.id,
                    target_quantity=payload.target_quantity,
                    unit=variant.base_unit,
                    request_id=payload.request_id,
                    request_payload=payload.model_dump(mode="json"),
                    status="open",
                    snapshot={
                        "supply_units": {
                            str(supply.id): supply.base_unit for supply in supplies
                        },
                        "recipe_name": recipe.name,
                        "recipe": plan.model_dump(mode="json"),
                        "planning": [step.model_dump(mode="json") for step in planning],
                        "configuration": configuration.model_dump(mode="json")
                        if configuration
                        else None,
                        "omitted_step_keys": omitted,
                        "machine_assignments": {
                            key: str(value)
                            for key, value in payload.machine_assignments.items()
                        },
                    },
                )
                self.session.add(item)
                self.session.flush()
                revisions: set[UUID] = set()
                for step in plan.steps:
                    self.session.add(
                        TestPrintStep(
                            test_print_id=item.id,
                            key=step.key,
                            planned_quantity=calculations[step.key].required_quantity,
                            unit=step.unit.value,
                            output_variant_id=step.output_variant_id,
                            machine_id=payload.machine_assignments.get(step.key),
                            snapshot=step.model_dump(mode="json"),
                        )
                    )
                    for resource in step.resources:
                        if not isinstance(resource, ResourceRead):
                            raise RunConflictError(
                                "La receta tiene recursos sin resolver"
                            )
                        revisions.add(resource.asset_revision_id)
                self.session.add_all(
                    [
                        TestPrintAssetRevision(
                            test_print_id=item.id, asset_revision_id=revision
                        )
                        for revision in revisions
                    ]
                )
                self.session.commit()
                self.session.refresh(item)
                return item
            except SQLAlchemyError as error:
                self.session.rollback()
                retryable = isinstance(error, DBAPIError) and (
                    getattr(error.orig, "sqlstate", None) in {"40001", "40P01"}
                    or (
                        getattr(error.orig, "sqlstate", None) == "23505"
                        and getattr(
                            getattr(error.orig, "diag", None), "constraint_name", None
                        )
                        == "uq_test_prints_request_id"
                    )
                )
                if retryable and attempt < 2:
                    continue
                self._failure(error)
            except Exception:
                self.session.rollback()
                raise
        raise AssertionError("Reintentos agotados")

    def start(self, print_id: UUID, key: str, payload: RunCreate) -> ProductionRun:
        try:
            item = self.get(print_id, lock=True)
            steps = {step.key: step for step in self.steps(item.id)}
            step = steps.get(key)
            if step is None:
                raise RunNotFoundError("El paso no pertenece a esta prueba")
            runs = ProductionRunService(self.session)
            original = runs.repository.by_request(payload.request_id)
            request = payload.model_dump(mode="json", exclude_unset=True)
            if original is not None:
                if (
                    original.test_print_step_id != step.id
                    or original.request_payload != request
                ):
                    raise RunConflictError("La petición corresponde a otro intento")
                return original
            if item.status != "open" or self.open_run(step.id) is not None:
                raise RunConflictError("La prueba o el paso no admite otro intento")
            definition = StepRead.model_validate(step.snapshot)
            for prerequisite in definition.depends_on:
                parent = steps[prerequisite]
                if self.totals(parent.id)[0] < parent.planned_quantity or self.open_run(
                    parent.id
                ):
                    raise RunConflictError("Hay prerrequisitos sin finalizar")
            machine_id = (
                payload.machine_id
                if "machine_id" in payload.model_fields_set
                else step.machine_id
            )
            if definition.kind.value in {"service", "wait"} and machine_id is not None:
                raise RunConflictError("Service y wait no asignan máquina")
            required = (
                definition.required_machine_type.value
                if definition.required_machine_type
                else None
            )
            if definition.kind.value == "print" and required is None:
                required = (
                    "fdm_printer"
                    if definition.task_type.value == "fdm_print"
                    else "sla_printer"
                )
            runs._machine(machine_id, required_type=required)
            now = datetime.now(UTC)
            started = payload.started_at or now
            if started > now:
                raise RunConflictError("El inicio no puede estar en el futuro")
            # No solapar intentos del paso ni anticiparse al cierre de prerrequisitos.
            prior_ids = [
                step.id,
                *(steps[parent].id for parent in definition.depends_on),
            ]
            last_end = self.session.scalar(
                select(func.max(ProductionRun.ended_at)).where(
                    ProductionRun.test_print_step_id.in_(prior_ids)
                )
            )
            if last_end is not None and started < last_end:
                raise RunConflictError("El inicio precede a un intento o prerrequisito")
            run = ProductionRun(
                task_id=None,
                test_print_step_id=step.id,
                request_id=payload.request_id,
                request_payload=request,
                machine_id=machine_id,
                output_variant_id=step.output_variant_id,
                unit=step.unit,
                parameters=payload.parameters
                if payload.parameters is not None
                else definition.parameters,
                started_at=started,
                status="running",
            )
            self.session.add(run)
            self.session.commit()
            self.session.refresh(run)
            return run
        except SQLAlchemyError as error:
            self._failure(error)
        except Exception:
            self.session.rollback()
            raise

    def close_run(self, run_id: UUID, payload: RunClose) -> ProductionRun:
        try:
            runs = ProductionRunService(self.session)
            existing = runs.get(run_id)
            step = self.session.get(TestPrintStep, existing.test_print_step_id)
            if step is None:
                raise RunNotFoundError("No existe el paso experimental")
            item = self.get(step.test_print_id, lock=True)
            run = runs.get(run_id, lock=True)
            if run.status == "closed":
                if (
                    run.result_payload is None
                    or RunClose.model_validate(run.result_payload) != payload
                ):
                    raise RunConflictError("La ejecución ya tiene otro resultado")
                return run
            definition = StepRead.model_validate(step.snapshot)
            if payload.good_quantity > 0 and (
                not {value.supply_id for value in definition.supply_inputs}
                <= {value.supply_id for value in payload.supply_consumptions}
                or not {value.product_variant_id for value in definition.product_inputs}
                <= {value.variant_id for value in payload.product_consumptions}
            ):
                raise RunConflictError("Registre los consumos obligatorios del paso")
            # La receta pudo editarse desde la creación; no consumir otra unidad.
            for value in sorted(
                payload.supply_consumptions, key=lambda value: value.supply_id
            ):
                supply = self.session.scalar(
                    select(Supply)
                    .where(Supply.id == value.supply_id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
                frozen_unit = item.snapshot["supply_units"].get(str(value.supply_id))
                if (
                    supply is not None
                    and frozen_unit is not None
                    and supply.base_unit != frozen_unit
                ):
                    raise RunConflictError(
                        "La unidad del insumo cambió desde la prueba"
                    )
            ended = payload.ended_at or datetime.now(UTC)
            if ended < run.started_at or ended > datetime.now(UTC):
                raise RunConflictError(
                    "El fin debe estar entre el inicio y el momento actual"
                )
            elapsed = ended - run.started_at
            run.ended_at = ended
            run.actual_duration_seconds = (
                payload.actual_duration_seconds
                if payload.actual_duration_seconds is not None
                else (
                    Decimal(elapsed.days * 86400 + elapsed.seconds)
                    + Decimal(elapsed.microseconds) / Decimal(1000000)
                )
            )
            run.good_quantity = payload.good_quantity
            run.failed_quantity = payload.failed_quantity
            run.failure_reason = (
                payload.failure_reason.value if payload.failure_reason else None
            )
            run.notes = payload.notes
            run.result_payload = payload.model_dump(mode="json")
            run.status = "closed"
            self.session.flush()
            RunSupplyConsumptionService(self.session).record(
                run, payload.supply_consumptions, ended
            )
            external = self._internal_consumptions(
                item, step, run, payload.product_consumptions
            )
            RunProductConsumptionService(self.session).record(run, external, ended)
            run.warnings = [
                "insufficient_supply_stock:" + str(value.supply_id)
                for value in payload.supply_consumptions
                if SupplyReservationService(self.session)
                .availability(value.supply_id)
                .shortage_warning
            ]
            run.warnings += [
                "insufficient_product_stock:" + str(value.variant_id)
                for value in external
                if ProductStockService(self.session)
                .stock(value.variant_id)
                .shortage_warning
            ]
            if all(
                self.totals(value.id)[0] >= value.planned_quantity
                and self.open_run(value.id) is None
                for value in self.steps(item.id)
            ):
                item.status = "completed"
            self.session.commit()
            self.session.refresh(run)
            return run
        except SQLAlchemyError as error:
            self._failure(error)
        except Exception:
            self.session.rollback()
            raise

    def _internal_consumptions(
        self,
        item: TestPrint,
        step: TestPrintStep,
        run: ProductionRun,
        consumptions: list[RunProductConsumptionCreate],
    ) -> list[RunProductConsumptionCreate]:
        definition = StepRead.model_validate(step.snapshot)
        sources = {
            value.product_variant_id: value.source_step_key
            for value in definition.product_inputs
            if value.source_step_key is not None
        }
        steps = {value.key: value for value in self.steps(item.id)}
        external = []
        for value in consumptions:
            source_key = sources.get(value.variant_id)
            if source_key is None:
                external.append(value)
                continue
            source = steps[source_key]
            used = self.session.scalar(
                select(
                    func.coalesce(func.sum(ProductionRunProductConsumption.consumed), 0)
                ).where(
                    ProductionRunProductConsumption.internal_source_step_id == source.id
                )
            )
            available = self.totals(source.id)[0] - Decimal(used or 0)
            if value.consumed > available:
                raise RunConflictError(
                    "No hay suficientes componentes internos de la prueba"
                )
            self.session.add(
                ProductionRunProductConsumption(
                    run_id=run.id,
                    variant_id=value.variant_id,
                    consumed=value.consumed,
                    wasted=value.wasted,
                    unit=source.unit,
                    internal_source_step_id=source.id,
                )
            )
        self.session.flush()
        return external

    def promote(
        self, print_id: UUID, payload: TestPrintPromotion
    ) -> ProductStockMovement:
        try:
            item = self.get(print_id, lock=True)
            original = self.session.scalar(
                select(ProductStockMovement).where(
                    ProductStockMovement.test_print_id == item.id
                )
            )
            if original is not None:
                if (
                    original.request_id != payload.request_id
                    or original.quantity != payload.quantity
                ):
                    raise RunConflictError("La prueba ya tiene otra promoción")
                return original
            if item.status != "completed":
                raise RunConflictError(
                    "Debe completar todos los pasos antes de promover"
                )
            final_steps = [
                step
                for step in self.steps(item.id)
                if step.output_variant_id == item.variant_id
            ]
            if len(final_steps) != 1 or payload.quantity > self.available_internal(
                final_steps[0].id
            ):
                raise RunConflictError(
                    "La promoción supera las unidades buenas finales"
                )
            variant = self.session.scalar(
                select(ProductVariant)
                .where(ProductVariant.id == item.variant_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if variant is None or not variant.active or variant.base_unit != item.unit:
                raise RunConflictError(
                    "La variante destino está inactiva o su unidad no coincide"
                )
            movement = ProductStockMovement(
                variant_id=item.variant_id,
                test_print_id=item.id,
                quantity=payload.quantity,
                unit=item.unit,
                movement_type="test_print",
                request_id=payload.request_id,
                request_payload=payload.model_dump(mode="json"),
                reason="Promoción explícita de prueba de receta",
                occurred_at=datetime.now(UTC),
            )
            self.session.add(movement)
            self.session.commit()
            self.session.refresh(movement)
            return movement
        except SQLAlchemyError as error:
            self._failure(error)
        except Exception:
            self.session.rollback()
            raise

    def cancel(self, print_id: UUID) -> TestPrint:
        try:
            item = self.get(print_id, lock=True)
            if item.status == "cancelled":
                return item
            if item.status != "open" or any(
                self.open_run(step.id) for step in self.steps(item.id)
            ):
                raise RunConflictError(
                    "Sólo se cancela una prueba abierta sin intentos abiertos"
                )
            item.status = "cancelled"
            self.session.commit()
            return item
        except SQLAlchemyError as error:
            self._failure(error)
        except Exception:
            self.session.rollback()
            raise

    @staticmethod
    def _whole_units(value: Decimal, unit: str) -> None:
        if unit == "unit" and value != value.to_integral_value():
            raise RunConflictError("La cantidad en unidades debe ser entera")

    def _failure(self, error: SQLAlchemyError) -> NoReturn:
        self.session.rollback()
        if isinstance(error, IntegrityError) or (
            isinstance(error, DBAPIError)
            and getattr(error.orig, "sqlstate", None) in {"40001", "40P01"}
        ):
            raise RunConflictError(
                "Conflicto concurrente de prueba; reintentar la petición"
            ) from error
        raise PersistenceError("No se pudo guardar la prueba de receta") from error
