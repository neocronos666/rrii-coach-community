import builtins
from uuid import UUID

from sqlalchemy import case, select
from sqlalchemy.orm import Session, joinedload

from app.modules.machines.models import Machine
from app.modules.orders.models import Order
from app.modules.production.models import (
    ProductionTask,
    ProductionTaskDependency,
    production_task_code_sequence,
)
from app.modules.production.run_models import ProductionRun
from app.modules.production.types import ProductionTaskPriority, ProductionTaskStatus
from app.modules.projects.models import ProjectComponent


class ProductionTaskRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def next_code(self, year: int) -> str:
        number = self._session.scalar(production_task_code_sequence.next_value())
        if number is None:
            raise RuntimeError("No se pudo generar el código de tarea")
        return f"T-{year}-{number:06d}"

    def add(self, task: ProductionTask) -> ProductionTask:
        self._session.add(task)
        self._session.flush()
        return task

    def get_by_id(
        self, task_id: UUID, *, for_update: bool = False
    ) -> ProductionTask | None:
        statement = select(ProductionTask).where(ProductionTask.id == task_id)
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return self._session.scalar(statement)

    def get_machine(self, machine_id: UUID) -> Machine | None:
        return self._session.scalar(
            select(Machine).where(Machine.id == machine_id).with_for_update()
        )

    def get_order(self, order_id: UUID) -> Order | None:
        return self._session.get(Order, order_id)

    def get_project_component(self, component_id: UUID) -> ProjectComponent | None:
        statement = (
            select(ProjectComponent)
            .options(joinedload(ProjectComponent.project))
            .where(ProjectComponent.id == component_id)
        )
        return self._session.scalar(statement)

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
        priority_rank = case(
            {
                ProductionTaskPriority.URGENT.value: 4,
                ProductionTaskPriority.HIGH.value: 3,
                ProductionTaskPriority.NORMAL.value: 2,
                ProductionTaskPriority.LOW.value: 1,
            },
            value=ProductionTask.priority,
            else_=0,
        )
        statement = select(ProductionTask)
        if status is not None:
            statement = statement.where(ProductionTask.status == status.value)
        if priority is not None:
            statement = statement.where(ProductionTask.priority == priority.value)
        if machine_id is not None:
            statement = statement.where(ProductionTask.machine_id == machine_id)
        if order_id is not None:
            statement = statement.where(ProductionTask.order_id == order_id)
        if project_component_id is not None:
            statement = statement.where(
                ProductionTask.project_component_id == project_component_id
            )
        if project_id is not None:
            statement = statement.join(
                ProjectComponent,
                ProductionTask.project_component_id == ProjectComponent.id,
            ).where(ProjectComponent.project_id == project_id)
        statement = statement.order_by(
            priority_rank.desc(),
            ProductionTask.queue_position,
            ProductionTask.created_at,
            ProductionTask.id,
        )
        return list(self._session.scalars(statement))

    def machine_is_busy(
        self, machine_id: UUID, *, excluding: UUID | None = None
    ) -> bool:
        statement = select(ProductionTask.id).where(
            ProductionTask.machine_id == machine_id,
            ProductionTask.status == "in_progress",
            ProductionTask.execution_mode == "legacy",
        )
        if excluding is not None:
            statement = statement.where(ProductionTask.id != excluding)
        if self._session.scalar(statement.limit(1)) is not None:
            return True
        return (
            self._session.scalar(
                select(ProductionRun.id)
                .where(
                    ProductionRun.machine_id == machine_id,
                    ProductionRun.status == "running",
                )
                .limit(1)
            )
            is not None
        )

    def project_id_for_component(self, component_id: UUID) -> UUID | None:
        return self._session.scalar(
            select(ProjectComponent.project_id).where(
                ProjectComponent.id == component_id
            )
        )

    def add_dependency(
        self, dependency: ProductionTaskDependency
    ) -> ProductionTaskDependency:
        self._session.add(dependency)
        self._session.flush()
        return dependency

    def get_dependency(
        self, task_id: UUID, depends_on_task_id: UUID
    ) -> ProductionTaskDependency | None:
        return self._session.get(
            ProductionTaskDependency,
            (task_id, depends_on_task_id),
        )

    def remove_dependency(self, dependency: ProductionTaskDependency) -> None:
        self._session.delete(dependency)
        self._session.flush()

    def list_dependencies(
        self, task_id: UUID
    ) -> builtins.list[ProductionTaskDependency]:
        statement = (
            select(ProductionTaskDependency)
            .options(joinedload(ProductionTaskDependency.prerequisite))
            .where(ProductionTaskDependency.task_id == task_id)
            .order_by(
                ProductionTaskDependency.created_at,
                ProductionTaskDependency.depends_on_task_id,
            )
        )
        return list(self._session.scalars(statement))

    def list_dependency_ids(self, task_id: UUID) -> builtins.list[UUID]:
        statement = select(ProductionTaskDependency.depends_on_task_id).where(
            ProductionTaskDependency.task_id == task_id
        )
        return list(self._session.scalars(statement))

    def list_unsatisfied_dependency_ids(self, task_id: UUID) -> builtins.list[UUID]:
        statement = (
            select(ProductionTaskDependency.depends_on_task_id)
            .join(
                ProductionTask,
                ProductionTask.id == ProductionTaskDependency.depends_on_task_id,
            )
            .where(
                ProductionTaskDependency.task_id == task_id,
                ProductionTask.status
                != ProductionTaskStatus.PHYSICALLY_COMPLETED.value,
            )
        )
        return list(self._session.scalars(statement))
