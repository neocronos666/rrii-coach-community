from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.modules.products.allocation_schemas import (
    AllocationCreate,
    AllocationDelivery,
    AllocationRead,
    AllocationResult,
)
from app.modules.products.allocation_service import ProductAllocationService
from app.modules.products.stock_router import DatabaseSession, errors
from app.modules.products.stock_schemas import StockMovementRead
from app.modules.products.stock_service import ProductStockService

router = APIRouter(tags=["product-allocations"])


@router.post("/product-allocations", response_model=AllocationResult, status_code=201)
def create_allocation(
    payload: AllocationCreate, session: DatabaseSession
) -> AllocationResult:
    with errors():
        allocation = ProductAllocationService(session).create(payload)
        return AllocationResult(
            allocation=AllocationRead.model_validate(allocation),
            stock=ProductStockService(session).stock(allocation.variant_id),
        )


@router.get("/product-allocations", response_model=list[AllocationRead])
def list_allocations(
    session: DatabaseSession,
    order_id: UUID | None = None,
    project_component_id: UUID | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[AllocationRead]:
    return [
        AllocationRead.model_validate(item)
        for item in ProductAllocationService(session).list_allocations(
            order_id, project_component_id, offset, limit
        )
    ]


@router.get("/product-allocations/{allocation_id}", response_model=AllocationRead)
def get_allocation(allocation_id: UUID, session: DatabaseSession) -> AllocationRead:
    with errors():
        return AllocationRead.model_validate(
            ProductAllocationService(session).get(allocation_id)
        )


@router.post(
    "/product-allocations/{allocation_id}/release", response_model=AllocationRead
)
def release_allocation(allocation_id: UUID, session: DatabaseSession) -> AllocationRead:
    with errors():
        return AllocationRead.model_validate(
            ProductAllocationService(session).release(allocation_id)
        )


@router.post(
    "/product-allocations/{allocation_id}/deliver",
    response_model=StockMovementRead,
    status_code=201,
)
def deliver_allocation(
    allocation_id: UUID, payload: AllocationDelivery, session: DatabaseSession
) -> StockMovementRead:
    with errors():
        return StockMovementRead.model_validate(
            ProductAllocationService(session).deliver(allocation_id, payload)
        )
