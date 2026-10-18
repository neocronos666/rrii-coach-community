from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.db.session import get_db_session
from app.modules.production.exceptions import ProductionTaskNotFoundError
from app.modules.supplies.exceptions import SupplyNotFoundError
from app.modules.supplies.reservation_schemas import (
    ReservationRead,
    ReservationResult,
    ReservationSet,
    SupplyAvailabilityRead,
)
from app.modules.supplies.reservation_service import (
    ReservationConflictError,
    SupplyReservationService,
)

router = APIRouter(tags=["supply-reservations"])


def reservation_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> SupplyReservationService:
    return SupplyReservationService(session)


Service = Annotated[SupplyReservationService, Depends(reservation_service)]


@contextmanager
def errors() -> Iterator[None]:
    try:
        yield
    except (ProductionTaskNotFoundError, SupplyNotFoundError) as error:
        raise HTTPException(404, str(error)) from error
    except ReservationConflictError as error:
        raise HTTPException(409, str(error)) from error
    except PersistenceError as error:
        raise HTTPException(500, "No se pudo guardar la reserva") from error


@router.put(
    "/production-tasks/{task_id}/supply-reservations/{supply_id}",
    response_model=ReservationResult,
)
def set_reservation(
    task_id: UUID, supply_id: UUID, payload: ReservationSet, service: Service
) -> ReservationResult:
    with errors():
        return service.set(task_id, supply_id, payload)


@router.get(
    "/production-tasks/{task_id}/supply-reservations",
    response_model=list[ReservationRead],
)
def list_reservations(task_id: UUID, service: Service) -> list[ReservationRead]:
    with errors():
        return [
            ReservationRead.model_validate(reservation)
            for reservation in service.list(task_id)
        ]


@router.get("/supplies/{supply_id}/availability", response_model=SupplyAvailabilityRead)
def get_availability(supply_id: UUID, service: Service) -> SupplyAvailabilityRead:
    with errors():
        return service.availability(supply_id)
