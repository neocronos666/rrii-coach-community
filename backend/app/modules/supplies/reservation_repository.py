from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.modules.production.models import ProductionTask
from app.modules.projects.models import ProjectComponent
from app.modules.supplies.reservation_models import SupplyReservation


class SupplyReservationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, task_id: UUID, supply_id: UUID) -> SupplyReservation | None:
        return self.session.scalar(
            select(SupplyReservation)
            .where(
                SupplyReservation.task_id == task_id,
                SupplyReservation.supply_id == supply_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def list(self, task_id: UUID) -> list[SupplyReservation]:
        return list(
            self.session.scalars(
                select(SupplyReservation)
                .where(SupplyReservation.task_id == task_id)
                .order_by(SupplyReservation.supply_id)
            )
        )

    def reserved(self, supply_id: UUID) -> Decimal:
        value = self.session.scalar(
            select(func.coalesce(func.sum(SupplyReservation.quantity), 0)).where(
                SupplyReservation.supply_id == supply_id
            )
        )
        return Decimal(value or 0)

    def release_task(self, task_id: UUID) -> None:
        self.session.execute(
            update(SupplyReservation)
            .where(SupplyReservation.task_id == task_id)
            .values(quantity=Decimal(0))
        )

    def release_order(self, order_id: UUID) -> None:
        tasks = select(ProductionTask.id).where(ProductionTask.order_id == order_id)
        self.session.execute(
            update(SupplyReservation)
            .where(SupplyReservation.task_id.in_(tasks))
            .values(quantity=Decimal(0))
        )

    def release_project(self, project_id: UUID) -> None:
        tasks = (
            select(ProductionTask.id)
            .join(
                ProjectComponent,
                ProductionTask.project_component_id == ProjectComponent.id,
            )
            .where(ProjectComponent.project_id == project_id)
        )
        self.session.execute(
            update(SupplyReservation)
            .where(SupplyReservation.task_id.in_(tasks))
            .values(quantity=Decimal(0))
        )
