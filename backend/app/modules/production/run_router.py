from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.db.session import get_db_session
from app.modules.production.exceptions import ProductionTaskNotFoundError
from app.modules.production.run_exceptions import RunConflictError, RunNotFoundError
from app.modules.production.run_schemas import (
    RunClose,
    RunCreate,
    RunRead,
    TaskProgressRead,
)
from app.modules.production.run_service import ProductionRunService
from app.modules.products.consumption_schemas import RunProductConsumptionRead
from app.modules.products.consumption_service import RunProductConsumptionService
from app.modules.products.exceptions import ProductNotFoundError
from app.modules.products.stock_service import ProductStockConflictError
from app.modules.supplies.consumption_schemas import RunSupplyConsumptionRead
from app.modules.supplies.consumption_service import RunSupplyConsumptionService
from app.modules.supplies.exceptions import SupplyNotFoundError

router = APIRouter(tags=["production-runs"])


def run_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> ProductionRunService:
    return ProductionRunService(session)


Service = Annotated[ProductionRunService, Depends(run_service)]


@contextmanager
def errors() -> Iterator[None]:
    try:
        yield
    except (
        RunNotFoundError,
        ProductionTaskNotFoundError,
        SupplyNotFoundError,
        ProductNotFoundError,
    ) as error:
        raise HTTPException(404, str(error)) from error
    except (RunConflictError, ProductStockConflictError) as error:
        raise HTTPException(409, str(error)) from error
    except PersistenceError as error:
        raise HTTPException(500, "No se pudo guardar la ejecución") from error


@router.post(
    "/production-tasks/{task_id}/runs", response_model=RunRead, status_code=201
)
def start_run(task_id: UUID, payload: RunCreate, service: Service) -> RunRead:
    with errors():
        return RunRead.model_validate(service.start(task_id, payload))


@router.get("/production-tasks/{task_id}/runs", response_model=list[RunRead])
def list_runs(task_id: UUID, service: Service) -> list[RunRead]:
    with errors():
        service.task(task_id)
        return [RunRead.model_validate(run) for run in service.repository.list(task_id)]


@router.get("/production-runs/{run_id}", response_model=RunRead)
def get_run(run_id: UUID, service: Service) -> RunRead:
    with errors():
        return RunRead.model_validate(service.get(run_id))


@router.post("/production-runs/{run_id}/close", response_model=RunRead)
def close_run(run_id: UUID, payload: RunClose, service: Service) -> RunRead:
    with errors():
        return RunRead.model_validate(service.close(run_id, payload))


@router.get("/production-tasks/{task_id}/progress", response_model=TaskProgressRead)
def get_progress(task_id: UUID, service: Service) -> TaskProgressRead:
    with errors():
        return service.progress(task_id)


@router.get(
    "/production-runs/{run_id}/supply-consumptions",
    response_model=list[RunSupplyConsumptionRead],
)
def list_supply_consumptions(
    run_id: UUID, service: Service
) -> list[RunSupplyConsumptionRead]:
    with errors():
        service.get(run_id)
        return [
            RunSupplyConsumptionRead.model_validate(item)
            for item in RunSupplyConsumptionService(service.session).list_for_run(
                run_id
            )
        ]


@router.get(
    "/production-runs/{run_id}/product-consumptions",
    response_model=list[RunProductConsumptionRead],
)
def list_product_consumptions(
    run_id: UUID, service: Service
) -> list[RunProductConsumptionRead]:
    with errors():
        service.get(run_id)
        return [
            RunProductConsumptionRead.model_validate(item)
            for item in RunProductConsumptionService(service.session).list_for_run(
                run_id
            )
        ]
