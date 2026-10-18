from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.modules.production.run_exceptions import RunNotFoundError
from app.modules.production.run_models import ProductionRun
from app.modules.production.run_router import errors as run_errors
from app.modules.production.run_schemas import RunCreate, RunRead
from app.modules.production.test_print_models import TestPrint
from app.modules.production.test_print_schemas import (
    TestPrintCreate,
    TestPrintPromotion,
    TestPrintRead,
)
from app.modules.production.test_print_service import TestPrintService
from app.modules.products.stock_schemas import StockMovementRead
from app.modules.recipes.router import errors as recipe_errors

router = APIRouter(prefix="/test-prints", tags=["test-prints"])


def service(session: Annotated[Session, Depends(get_db_session)]) -> TestPrintService:
    return TestPrintService(session)


Service = Annotated[TestPrintService, Depends(service)]


@router.post("", response_model=TestPrintRead, status_code=201)
def create(payload: TestPrintCreate, service: Service) -> TestPrintRead:
    with recipe_errors(), run_errors():
        return service.read(service.create(payload))


@router.get("", response_model=list[TestPrintRead])
def list_tests(
    service: Service,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    variant_id: UUID | None = None,
) -> list[TestPrintRead]:
    query = (
        select(TestPrint)
        .order_by(TestPrint.created_at, TestPrint.id)
        .offset(offset)
        .limit(limit)
    )
    if variant_id is not None:
        query = query.where(TestPrint.variant_id == variant_id)
    with run_errors():
        return [service.read(item) for item in service.session.scalars(query)]


@router.get("/{print_id}", response_model=TestPrintRead)
def get(print_id: UUID, service: Service) -> TestPrintRead:
    with run_errors():
        return service.read(service.get(print_id))


@router.post("/{print_id}/steps/{key}/runs", response_model=RunRead, status_code=201)
def start(print_id: UUID, key: str, payload: RunCreate, service: Service) -> RunRead:
    with run_errors():
        return RunRead.model_validate(service.start(print_id, key, payload))


@router.get("/{print_id}/steps/{key}/runs", response_model=list[RunRead])
def runs(
    print_id: UUID,
    key: str,
    service: Service,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[RunRead]:
    with run_errors():
        service.get(print_id)
        step = next((step for step in service.steps(print_id) if step.key == key), None)
        if step is None:
            raise RunNotFoundError("El paso no pertenece a esta prueba")
        return [
            RunRead.model_validate(run)
            for run in service.session.scalars(
                select(ProductionRun)
                .where(ProductionRun.test_print_step_id == step.id)
                .order_by(ProductionRun.started_at, ProductionRun.id)
                .offset(offset)
                .limit(limit)
            )
        ]


@router.post("/{print_id}/promote", response_model=StockMovementRead, status_code=201)
def promote(
    print_id: UUID, payload: TestPrintPromotion, service: Service
) -> StockMovementRead:
    with run_errors():
        return StockMovementRead.model_validate(service.promote(print_id, payload))


@router.post("/{print_id}/cancel", response_model=TestPrintRead)
def cancel(print_id: UUID, service: Service) -> TestPrintRead:
    with run_errors():
        return service.read(service.cancel(print_id))
