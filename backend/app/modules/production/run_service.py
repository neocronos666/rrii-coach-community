from datetime import UTC, datetime
from decimal import Decimal
from typing import NoReturn
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.modules.machines.models import Machine
from app.modules.orders.models import Order
from app.modules.production.exceptions import ProductionTaskNotFoundError
from app.modules.production.models import ProductionTask
from app.modules.production.repository import ProductionTaskRepository
from app.modules.production.run_exceptions import RunConflictError, RunNotFoundError
from app.modules.production.run_models import ProductionRun
from app.modules.production.run_repository import ProductionRunRepository
from app.modules.production.run_schemas import RunClose, RunCreate, TaskProgressRead
from app.modules.products.consumption_service import RunProductConsumptionService
from app.modules.products.exceptions import ProductNotFoundError
from app.modules.products.stock_service import (
    ProductStockConflictError,
    ProductStockService,
)
from app.modules.projects.models import Project, ProjectComponent
from app.modules.supplies.consumption_service import RunSupplyConsumptionService
from app.modules.supplies.exceptions import SupplyNotFoundError
from app.modules.supplies.reservation_repository import SupplyReservationRepository
from app.modules.supplies.reservation_service import SupplyReservationService


class ProductionRunService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ProductionRunRepository(session)
        self.tasks = ProductionTaskRepository(session)

    def task(self, task_id: UUID, *, lock: bool = False) -> ProductionTask:
        task = self.tasks.get_by_id(task_id, for_update=lock)
        if task is None:
            raise ProductionTaskNotFoundError("No existe la tarea")
        return task

    def get(self, run_id: UUID, *, lock: bool = False) -> ProductionRun:
        run = self.repository.get(run_id, lock=lock)
        if run is None:
            raise RunNotFoundError("No existe la ejecución")
        return run

    def progress(self, task_id: UUID) -> TaskProgressRead:
        task = self.task(task_id)
        if task.execution_mode == "legacy":
            raise RunConflictError(
                "La tarea histórica no tiene mediciones de producción real"
            )
        good, failed, count = self.repository.totals(task_id)
        return TaskProgressRead(
            task_id=task_id,
            target_quantity=task.planned_quantity,
            good_quantity=good,
            failed_quantity=failed,
            remaining_quantity=max(Decimal(0), task.planned_quantity - good),
            excess_quantity=max(Decimal(0), good - task.planned_quantity),
            closed_runs=count,
        )

    def start(self, task_id: UUID, payload: RunCreate) -> ProductionRun:
        try:
            task = self.task(task_id, lock=True)
            original = self.repository.by_request(payload.request_id)
            request = payload.model_dump(mode="json", exclude_unset=True)
            if original:
                if original.task_id != task_id or original.request_payload != request:
                    raise RunConflictError(
                        "La clave de petición ya corresponde a otra ejecución"
                    )
                return original
            if task.execution_mode != "runs":
                raise RunConflictError(
                    "La tarea histórica conserva su lifecycle anterior"
                )
            if task.status not in {"queued", "in_progress"}:
                raise RunConflictError("La tarea no admite un intento nuevo")
            self._validate_origin(task)
            if self.repository.open_for_task(task_id):
                raise RunConflictError("La tarea ya tiene una ejecución abierta")
            if task.status == "queued" and self.tasks.list_unsatisfied_dependency_ids(
                task_id
            ):
                raise RunConflictError("Hay prerrequisitos sin finalizar")
            machine_id = (
                payload.machine_id
                if "machine_id" in payload.model_fields_set
                else task.machine_id
            )
            required_type = (
                (task.recipe_snapshot or {})
                .get("step", {})
                .get("required_machine_type")
            )
            self._machine(machine_id, required_type=required_type)
            now = datetime.now(UTC)
            started_at = payload.started_at or now
            if started_at > now:
                raise RunConflictError("El inicio no puede estar en el futuro")
            if task.started_at is not None and started_at < task.started_at:
                raise RunConflictError(
                    "El intento no puede preceder al inicio de la tarea"
                )
            last_end = self.session.scalar(
                select(func.max(ProductionRun.ended_at)).where(
                    ProductionRun.task_id == task_id
                )
            )
            if last_end is not None and started_at < last_end:
                raise RunConflictError("El intento no puede solaparse con uno anterior")
            run = ProductionRun(
                task_id=task.id,
                request_id=payload.request_id,
                request_payload=request,
                machine_id=machine_id,
                output_variant_id=task.output_variant_id,
                unit=task.planned_unit,
                parameters=payload.parameters
                if payload.parameters is not None
                else dict(task.production_parameters),
                started_at=started_at,
                status="running",
            )
            self.session.add(run)
            task.status = "in_progress"
            if task.started_at is None:
                task.started_at = started_at
            self.session.commit()
            return run
        except (RunConflictError, ProductionTaskNotFoundError):
            self.session.rollback()
            raise
        except SQLAlchemyError as error:
            self._failure(error)

    def close(self, run_id: UUID, payload: RunClose) -> ProductionRun:
        try:
            existing = self.get(run_id)
            if existing.test_print_step_id is not None:
                from app.modules.production.test_print_service import TestPrintService

                return TestPrintService(self.session).close_run(run_id, payload)
            if existing.task_id is None:
                raise RunConflictError("La ejecución no tiene origen")
            task = self.task(existing.task_id, lock=True)
            run = self.get(run_id, lock=True)
            if run.status == "closed":
                if (
                    run.result_payload is None
                    or RunClose.model_validate(run.result_payload) != payload
                ):
                    raise RunConflictError("La ejecución ya tiene otro resultado")
                return run
            if payload.good_quantity > 0 and task.origin == "recipe":
                step = (task.recipe_snapshot or {}).get("step", {})
                required_supplies = {
                    UUID(item["supply_id"]) for item in step.get("supply_inputs", [])
                }
                required_products = {
                    UUID(item["product_variant_id"])
                    for item in step.get("product_inputs", [])
                }
                if not required_supplies <= {
                    item.supply_id for item in payload.supply_consumptions
                } or not required_products <= {
                    item.variant_id for item in payload.product_consumptions
                }:
                    raise RunConflictError(
                        "Registre los consumos obligatorios del paso"
                    )
            now = datetime.now(UTC)
            ended_at = payload.ended_at or now
            if ended_at < run.started_at or ended_at > now:
                raise RunConflictError(
                    "El fin debe estar entre el inicio y el momento actual"
                )
            delta = ended_at - run.started_at
            duration = Decimal(delta.days * 86400 + delta.seconds) + Decimal(
                delta.microseconds
            ) / Decimal(1000000)
            run.good_quantity = payload.good_quantity
            run.failed_quantity = payload.failed_quantity
            run.failure_reason = (
                payload.failure_reason.value if payload.failure_reason else None
            )
            run.notes = payload.notes
            run.actual_duration_seconds = (
                payload.actual_duration_seconds
                if payload.actual_duration_seconds is not None
                else duration
            )
            run.ended_at = ended_at
            run.status = "closed"
            run.result_payload = payload.model_dump(mode="json")
            self.session.flush()
            RunSupplyConsumptionService(self.session).record(
                run, payload.supply_consumptions, ended_at
            )
            RunProductConsumptionService(self.session).record(
                run, payload.product_consumptions, ended_at
            )
            ProductStockService(self.session).record_production(run)
            good, _, _ = self.repository.totals(task.id)
            if good >= task.planned_quantity:
                task.status = "physically_completed"
                task.physically_completed_at = ended_at
                SupplyReservationRepository(self.session).release_task(task.id)
            availability = SupplyReservationService(self.session)
            run.warnings = [
                "insufficient_supply_stock:" + str(item.supply_id)
                for item in payload.supply_consumptions
                if availability.availability(item.supply_id).shortage_warning
            ]
            run.warnings += [
                "insufficient_product_stock:" + str(item.variant_id)
                for item in payload.product_consumptions
                if ProductStockService(self.session)
                .stock(item.variant_id)
                .shortage_warning
            ]
            self.session.commit()
            self.session.refresh(run)
            return run
        except (
            RunConflictError,
            RunNotFoundError,
            ProductionTaskNotFoundError,
            SupplyNotFoundError,
            ProductStockConflictError,
            ProductNotFoundError,
        ):
            self.session.rollback()
            raise
        except SQLAlchemyError as error:
            self._failure(error)

    def _validate_origin(self, task: ProductionTask) -> None:
        if task.order_id:
            order = self.session.scalar(
                select(Order).where(Order.id == task.order_id).with_for_update()
            )
            valid = order is not None and order.status != "cancelled"
        else:
            project = self.session.scalar(
                select(Project)
                .join(ProjectComponent)
                .where(ProjectComponent.id == task.project_component_id)
                .with_for_update(of=Project)
            )
            valid = project is not None and project.status != "cancelled"
        if not valid:
            raise RunConflictError("El trabajo de origen está cancelado o no existe")

    def _machine(
        self, machine_id: UUID | None, *, required_type: str | None = None
    ) -> None:
        if machine_id is None:
            if required_type is not None:
                raise RunConflictError("El paso requiere una máquina compatible")
            return
        machine = self.session.scalar(
            select(Machine).where(Machine.id == machine_id).with_for_update()
        )
        if machine is None or not machine.active:
            raise RunConflictError("La máquina no existe o está inactiva")
        if required_type is not None and machine.machine_type != required_type:
            raise RunConflictError("La máquina no cumple el tipo requerido por el plan")
        occupied = self.session.scalar(
            select(ProductionRun.id)
            .where(
                ProductionRun.machine_id == machine_id,
                ProductionRun.status == "running",
            )
            .limit(1)
        )
        legacy = self.session.scalar(
            select(ProductionTask.id)
            .where(
                ProductionTask.machine_id == machine_id,
                ProductionTask.execution_mode == "legacy",
                ProductionTask.status == "in_progress",
            )
            .limit(1)
        )
        if occupied or legacy:
            raise RunConflictError("La máquina está ocupada")

    def _failure(self, error: SQLAlchemyError) -> NoReturn:
        self.session.rollback()
        if isinstance(error, IntegrityError):
            raise RunConflictError(
                "Conflicto concurrente de ejecución; consulte el estado actual"
            ) from error
        raise PersistenceError("No se pudo guardar la ejecución") from error
