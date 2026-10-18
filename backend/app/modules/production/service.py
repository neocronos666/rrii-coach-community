import builtins
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.modules.machines.exceptions import MachineNotFoundError
from app.modules.orders.types import OrderStatus
from app.modules.production.exceptions import (
    InactiveMachineError,
    InvalidProductionTaskOriginError,
    InvalidProductionTaskTransitionError,
    MachineBusyError,
    ProductionTaskDependencyConflictError,
    ProductionTaskDependencyCycleError,
    ProductionTaskDependencyNotFoundError,
    ProductionTaskNotEditableError,
    ProductionTaskNotFoundError,
    ProductionTaskOriginNotFoundError,
    UnsatisfiedProductionTaskDependenciesError,
)
from app.modules.production.models import ProductionTask, ProductionTaskDependency
from app.modules.production.repository import ProductionTaskRepository
from app.modules.production.run_repository import ProductionRunRepository
from app.modules.production.schemas import ProductionTaskCreate
from app.modules.production.types import ProductionTaskPriority, ProductionTaskStatus
from app.modules.products.models import Product, ProductVariant
from app.modules.projects.types import ProjectStatus
from app.modules.supplies.reservation_repository import SupplyReservationRepository

logger = logging.getLogger(__name__)

EDITABLE_FIELDS = {
    "title",
    "description",
    "priority",
    "planned_quantity",
    "machine_id",
    "queue_position",
    "production_parameters",
    "notes",
}
EDITABLE_BY_STATUS = {
    ProductionTaskStatus.QUEUED: EDITABLE_FIELDS,
    ProductionTaskStatus.PAUSED: EDITABLE_FIELDS - {"planned_quantity"},
    ProductionTaskStatus.IN_PROGRESS: {"notes", "production_parameters"},
    ProductionTaskStatus.PHYSICALLY_COMPLETED: set(),
    ProductionTaskStatus.CANCELLED: set(),
}
TRANSITIONS = {
    (ProductionTaskStatus.QUEUED, "start"): ProductionTaskStatus.IN_PROGRESS,
    (ProductionTaskStatus.IN_PROGRESS, "pause"): ProductionTaskStatus.PAUSED,
    (ProductionTaskStatus.PAUSED, "resume"): ProductionTaskStatus.IN_PROGRESS,
    (
        ProductionTaskStatus.IN_PROGRESS,
        "finish",
    ): ProductionTaskStatus.PHYSICALLY_COMPLETED,
    (ProductionTaskStatus.QUEUED, "cancel"): ProductionTaskStatus.CANCELLED,
    (ProductionTaskStatus.IN_PROGRESS, "cancel"): ProductionTaskStatus.CANCELLED,
    (ProductionTaskStatus.PAUSED, "cancel"): ProductionTaskStatus.CANCELLED,
}
DOMAIN_ERRORS = (
    InactiveMachineError,
    InvalidProductionTaskTransitionError,
    MachineBusyError,
    MachineNotFoundError,
    InvalidProductionTaskOriginError,
    ProductionTaskNotEditableError,
    ProductionTaskNotFoundError,
    ProductionTaskOriginNotFoundError,
    ProductionTaskDependencyConflictError,
    ProductionTaskDependencyCycleError,
    ProductionTaskDependencyNotFoundError,
    UnsatisfiedProductionTaskDependenciesError,
)


class ProductionTaskService:
    def __init__(
        self,
        session: Session,
        repository: ProductionTaskRepository | None = None,
    ) -> None:
        self._session = session
        self._repository = repository or ProductionTaskRepository(session)

    def get(self, task_id: UUID, *, for_update: bool = False) -> ProductionTask:
        task = self._repository.get_by_id(task_id, for_update=for_update)
        if task is None:
            raise ProductionTaskNotFoundError("No existe la tarea de producción")
        return task

    def list(
        self,
        *,
        status: ProductionTaskStatus | None = None,
        priority: ProductionTaskPriority | None = None,
        machine_id: UUID | None = None,
        order_id: UUID | None = None,
        project_component_id: UUID | None = None,
        project_id: UUID | None = None,
    ) -> list[ProductionTask]:
        return self._repository.list(
            status=status,
            priority=priority,
            machine_id=machine_id,
            order_id=order_id,
            project_component_id=project_component_id,
            project_id=project_id,
        )

    def create_for_order(
        self, order_id: UUID, payload: ProductionTaskCreate
    ) -> ProductionTask:
        order = self._repository.get_order(order_id)
        if order is None:
            raise ProductionTaskOriginNotFoundError("No existe el pedido")
        if order.status == OrderStatus.CANCELLED.value:
            raise InvalidProductionTaskOriginError("El pedido está cancelado")
        return self._create(payload, order_id=order_id)

    def create_for_project_component(
        self, component_id: UUID, payload: ProductionTaskCreate
    ) -> ProductionTask:
        component = self._repository.get_project_component(component_id)
        if component is None:
            raise ProductionTaskOriginNotFoundError(
                "No existe el componente de proyecto"
            )
        if component.project.status == ProjectStatus.CANCELLED.value:
            raise InvalidProductionTaskOriginError("El proyecto está cancelado")
        return self._create(payload, project_component_id=component_id)

    def _create(
        self,
        payload: ProductionTaskCreate,
        *,
        order_id: UUID | None = None,
        project_component_id: UUID | None = None,
    ) -> ProductionTask:
        try:
            self._validate_machine(payload.machine_id)
            if payload.output_variant_id:
                variant = self._session.get(ProductVariant, payload.output_variant_id)
                product = (
                    self._session.get(Product, variant.product_id) if variant else None
                )
                if (
                    variant is None
                    or product is None
                    or not variant.active
                    or not product.active
                ):
                    raise InvalidProductionTaskOriginError(
                        "La variante de salida no existe o está inactiva"
                    )
                if payload.planned_unit != variant.base_unit:
                    raise InvalidProductionTaskOriginError(
                        "La tarea debe usar la unidad base de la variante"
                    )
            task = ProductionTask(
                output_variant_id=payload.output_variant_id,
                code=self._repository.next_code(datetime.now(UTC).year),
                order_id=order_id,
                project_component_id=project_component_id,
                task_type=payload.task_type.value,
                title=payload.title,
                description=payload.description,
                status=ProductionTaskStatus.QUEUED.value,
                priority=payload.priority.value,
                planned_quantity=payload.planned_quantity,
                planned_unit=payload.planned_unit,
                machine_id=payload.machine_id,
                queue_position=payload.queue_position,
                production_parameters=payload.production_parameters,
                notes=payload.notes,
            )
            self._repository.add(task)
            self._session.commit()
            logger.info("production_task_created task_id=%s", task.id)
            return task
        except DOMAIN_ERRORS:
            self._session.rollback()
            raise
        except SQLAlchemyError as error:
            self._session.rollback()
            raise PersistenceError("No se pudo crear la tarea") from error

    def update(self, task_id: UUID, changes: dict[str, Any]) -> ProductionTask:
        try:
            task = self.get(task_id, for_update=True)
            if task.origin == "recipe" and "planned_quantity" in changes:
                raise ProductionTaskNotEditableError(
                    "La cantidad generada pertenece al plan inmutable"
                )
            state = ProductionTaskStatus(task.status)
            unknown = changes.keys() - EDITABLE_FIELDS
            forbidden = changes.keys() - EDITABLE_BY_STATUS[state]
            if unknown or forbidden:
                fields = sorted(unknown | forbidden)
                raise ProductionTaskNotEditableError(
                    f"Campos no editables en {state.value}: {fields}"
                )
            if "machine_id" in changes:
                self._validate_machine(changes["machine_id"])
            priority = changes.get("priority")
            if isinstance(priority, ProductionTaskPriority):
                changes = {**changes, "priority": priority.value}
            for field, value in changes.items():
                setattr(task, field, value)
            self._session.commit()
            logger.info("production_task_updated task_id=%s", task.id)
            return task
        except DOMAIN_ERRORS:
            self._session.rollback()
            raise
        except SQLAlchemyError as error:
            self._session.rollback()
            raise PersistenceError("No se pudo actualizar la tarea") from error

    def get_dependencies(
        self, task_id: UUID
    ) -> builtins.list[ProductionTaskDependency]:
        self.get(task_id)
        return self._repository.list_dependencies(task_id)

    def add_dependency(
        self, task_id: UUID, depends_on_task_id: UUID
    ) -> ProductionTaskDependency:
        try:
            task = self.get(task_id, for_update=True)
            prerequisite = self.get(depends_on_task_id)
            self._validate_dependency_change(task)
            if task.id == prerequisite.id:
                raise ProductionTaskDependencyConflictError(
                    "Una tarea no puede depender de sí misma"
                )
            if prerequisite.status == ProductionTaskStatus.CANCELLED.value:
                raise ProductionTaskDependencyConflictError(
                    "Una tarea cancelada no puede agregarse como prerrequisito"
                )
            if self._work_identity(task) != self._work_identity(prerequisite):
                raise ProductionTaskDependencyConflictError(
                    "Las dependencias deben pertenecer al mismo trabajo"
                )
            if self._repository.get_dependency(task.id, prerequisite.id) is not None:
                raise ProductionTaskDependencyConflictError("La dependencia ya existe")
            if self._would_create_cycle(task.id, prerequisite.id):
                raise ProductionTaskDependencyCycleError(
                    "La dependencia produciría un ciclo"
                )
            dependency = self._repository.add_dependency(
                ProductionTaskDependency(
                    task_id=task.id,
                    depends_on_task_id=prerequisite.id,
                )
            )
            dependency.prerequisite = prerequisite
            self._session.commit()
            logger.info(
                "production_task_dependency_added task_id=%s depends_on_task_id=%s",
                task.id,
                prerequisite.id,
            )
            return dependency
        except DOMAIN_ERRORS:
            self._session.rollback()
            raise
        except IntegrityError as error:
            self._session.rollback()
            if "production_task_dependencies" in str(error.orig):
                raise ProductionTaskDependencyConflictError(
                    "La dependencia es inválida o ya existe"
                ) from error
            raise PersistenceError("No se pudo agregar la dependencia") from error
        except SQLAlchemyError as error:
            self._session.rollback()
            raise PersistenceError("No se pudo agregar la dependencia") from error

    def remove_dependency(self, task_id: UUID, depends_on_task_id: UUID) -> None:
        try:
            task = self.get(task_id, for_update=True)
            self._validate_dependency_change(task)
            dependency = self._repository.get_dependency(task_id, depends_on_task_id)
            if dependency is None:
                raise ProductionTaskDependencyNotFoundError("No existe la dependencia")
            self._repository.remove_dependency(dependency)
            self._session.commit()
            logger.info(
                "production_task_dependency_removed task_id=%s depends_on_task_id=%s",
                task_id,
                depends_on_task_id,
            )
        except DOMAIN_ERRORS:
            self._session.rollback()
            raise
        except SQLAlchemyError as error:
            self._session.rollback()
            raise PersistenceError("No se pudo eliminar la dependencia") from error

    def start(self, task_id: UUID) -> ProductionTask:
        return self._transition(task_id, "start")

    def pause(self, task_id: UUID) -> ProductionTask:
        return self._transition(task_id, "pause")

    def resume(self, task_id: UUID) -> ProductionTask:
        return self._transition(task_id, "resume")

    def finish(self, task_id: UUID) -> ProductionTask:
        return self._transition(task_id, "finish")

    def cancel(self, task_id: UUID) -> ProductionTask:
        return self._transition(task_id, "cancel")

    def _transition(self, task_id: UUID, action: str) -> ProductionTask:
        try:
            task = self.get(task_id, for_update=True)
            current = ProductionTaskStatus(task.status)
            target = TRANSITIONS.get((current, action))
            if target is None:
                raise InvalidProductionTaskTransitionError(
                    f"No se puede ejecutar {action} desde {current.value}"
                )
            if action == "start":
                unsatisfied = self._repository.list_unsatisfied_dependency_ids(task.id)
                if unsatisfied:
                    raise UnsatisfiedProductionTaskDependenciesError(
                        "La tarea tiene prerrequisitos sin finalizar: "
                        + ", ".join(str(value) for value in unsatisfied)
                    )
            if task.execution_mode == "runs":
                runs = ProductionRunRepository(self._session)
                if action == "finish":
                    raise InvalidProductionTaskTransitionError(
                        "El cierre físico se calcula al cerrar las ejecuciones"
                    )
                if action in {"pause", "cancel"} and runs.open_for_task(task.id):
                    raise InvalidProductionTaskTransitionError(
                        "Cierre primero la ejecución abierta"
                    )
            if action in {"start", "resume"} and task.execution_mode == "legacy":
                self._validate_machine(
                    task.machine_id, available=True, excluding=task.id
                )
            now = datetime.now(UTC)
            if action == "start":
                task.started_at = task.started_at or now
            elif action == "pause":
                task.paused_at = now
            elif action == "finish":
                task.physically_completed_at = now
            elif action == "cancel":
                task.cancelled_at = now
                SupplyReservationRepository(self._session).release_task(task.id)
            task.status = target.value
            self._session.commit()
            event = "physically_completed" if action == "finish" else action
            logger.info("production_task_%s task_id=%s", event, task.id)
            return task
        except DOMAIN_ERRORS:
            self._session.rollback()
            raise
        except IntegrityError as error:
            self._session.rollback()
            if "uq_production_tasks_machine_in_progress" in str(error.orig):
                raise MachineBusyError(
                    "La máquina ya tiene una tarea en progreso"
                ) from error
            raise PersistenceError(
                "No se pudo cambiar el estado de la tarea"
            ) from error
        except SQLAlchemyError as error:
            self._session.rollback()
            raise PersistenceError(
                "No se pudo cambiar el estado de la tarea"
            ) from error

    def _validate_machine(
        self,
        machine_id: UUID | None,
        *,
        available: bool = False,
        excluding: UUID | None = None,
    ) -> None:
        if machine_id is None:
            return
        machine = self._repository.get_machine(machine_id)
        if machine is None:
            raise MachineNotFoundError("No existe la máquina")
        if not machine.active:
            raise InactiveMachineError("La máquina está inactiva")
        if available and self._repository.machine_is_busy(
            machine_id, excluding=excluding
        ):
            raise MachineBusyError("La máquina ya tiene una tarea en progreso")

    def _validate_dependency_change(self, task: ProductionTask) -> None:
        if task.origin == "recipe":
            raise ProductionTaskDependencyConflictError(
                "Las dependencias generadas pertenecen al plan inmutable"
            )
        if task.status != ProductionTaskStatus.QUEUED.value:
            raise ProductionTaskDependencyConflictError(
                "Las dependencias sólo pueden modificarse en estado queued"
            )

    def _work_identity(self, task: ProductionTask) -> tuple[str, UUID]:
        if task.order_id is not None:
            return ("order", task.order_id)
        if task.project_component_id is None:
            raise InvalidProductionTaskOriginError("La tarea no tiene origen válido")
        project_id = self._repository.project_id_for_component(
            task.project_component_id
        )
        if project_id is None:
            raise InvalidProductionTaskOriginError("No existe el proyecto de la tarea")
        return ("project", project_id)

    def _would_create_cycle(self, task_id: UUID, prerequisite_id: UUID) -> bool:
        pending = [prerequisite_id]
        visited: set[UUID] = set()
        while pending:
            current = pending.pop()
            if current == task_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            pending.extend(self._repository.list_dependency_ids(current))
        return False
