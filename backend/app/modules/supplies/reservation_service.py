from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.modules.orders.models import Order
from app.modules.production.exceptions import ProductionTaskNotFoundError
from app.modules.production.models import ProductionTask
from app.modules.production.repository import ProductionTaskRepository
from app.modules.projects.models import Project, ProjectComponent
from app.modules.supplies.exceptions import SupplyNotFoundError
from app.modules.supplies.repository import StockMovementRepository, SupplyRepository
from app.modules.supplies.reservation_models import SupplyReservation
from app.modules.supplies.reservation_repository import SupplyReservationRepository
from app.modules.supplies.reservation_schemas import (
    ReservationRead,
    ReservationResult,
    ReservationSet,
    SupplyAvailabilityRead,
)
from app.modules.supplies.schemas import SupplyUnit


class ReservationConflictError(Exception):
    pass


class SupplyReservationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = SupplyReservationRepository(session)
        self.supplies = SupplyRepository(session)
        self.tasks = ProductionTaskRepository(session)

    def list(self, task_id: UUID) -> list[SupplyReservation]:
        if self.tasks.get_by_id(task_id) is None:
            raise ProductionTaskNotFoundError("No existe la tarea")
        return self.repository.list(task_id)

    def availability(self, supply_id: UUID) -> SupplyAvailabilityRead:
        supply = self.supplies.get(supply_id, for_update=True)
        if supply is None:
            raise SupplyNotFoundError("No existe el insumo")
        physical = StockMovementRepository(self.session).stock(supply_id)
        reserved = self.repository.reserved(supply_id)
        return SupplyAvailabilityRead(
            supply_id=supply_id,
            unit=SupplyUnit(supply.base_unit),
            physical_quantity=physical,
            reserved_quantity=reserved,
            available_quantity=physical - reserved,
            shortage_warning=physical < reserved,
        )

    def set(
        self, task_id: UUID, supply_id: UUID, payload: ReservationSet
    ) -> ReservationResult:
        try:
            task = self.tasks.get_by_id(task_id, for_update=True)
            if task is None:
                raise ProductionTaskNotFoundError("No existe la tarea")
            if payload.quantity > 0:
                self._validate_task(task)
            supply = self.supplies.get(supply_id, for_update=True)
            if supply is None:
                raise SupplyNotFoundError("No existe el insumo")
            if not supply.active and payload.quantity > 0:
                raise ReservationConflictError("El insumo está inactivo")
            reservation = self.repository.get(task_id, supply_id)
            if reservation is None:
                reservation = SupplyReservation(
                    task_id=task_id,
                    supply_id=supply_id,
                    quantity=payload.quantity,
                    unit=supply.base_unit,
                )
                self.session.add(reservation)
            else:
                reservation.quantity = payload.quantity
            self.session.flush()
            availability = self.availability(supply_id)
            self.session.commit()
            self.session.refresh(reservation)
            return ReservationResult(
                reservation=ReservationRead.model_validate(reservation),
                availability=availability,
            )
        except (
            ProductionTaskNotFoundError,
            SupplyNotFoundError,
            ReservationConflictError,
        ):
            self.session.rollback()
            raise
        except SQLAlchemyError as error:
            self.session.rollback()
            raise PersistenceError("No se pudo guardar la reserva") from error

    def _validate_task(self, task: ProductionTask) -> None:
        if task.execution_mode != "runs" or task.status in {
            "physically_completed",
            "cancelled",
        }:
            raise ReservationConflictError("La tarea no admite nuevas reservas")
        if task.order_id:
            order = self.session.scalar(
                select(Order).where(Order.id == task.order_id).with_for_update()
            )
            active = order is not None and order.status != "cancelled"
        else:
            project = self.session.scalar(
                select(Project)
                .join(ProjectComponent)
                .where(ProjectComponent.id == task.project_component_id)
                .with_for_update(of=Project)
            )
            active = project is not None and project.status != "cancelled"
        if not active:
            raise ReservationConflictError("El trabajo de origen está cancelado")
