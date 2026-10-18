from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.db.session import get_db_session
from app.modules.products.exceptions import ProductNotFoundError
from app.modules.products.stock_schemas import (
    ProductStockRead,
    StockMovementCreate,
    StockMovementRead,
)
from app.modules.products.stock_service import (
    ProductStockConflictError,
    ProductStockService,
)

router = APIRouter(tags=["product-stock"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]


@contextmanager
def errors() -> Iterator[None]:
    try:
        yield
    except ProductNotFoundError as error:
        raise HTTPException(404, str(error)) from error
    except ProductStockConflictError as error:
        raise HTTPException(409, str(error)) from error
    except PersistenceError as error:
        raise HTTPException(500, str(error)) from error


@router.post(
    "/product-variants/{variant_id}/stock-movements",
    response_model=StockMovementRead,
    status_code=201,
)
def create_movement(
    variant_id: UUID, payload: StockMovementCreate, session: DatabaseSession
) -> StockMovementRead:
    with errors():
        return StockMovementRead.model_validate(
            ProductStockService(session).create(variant_id, payload)
        )


@router.get(
    "/product-variants/{variant_id}/stock-movements",
    response_model=list[StockMovementRead],
)
def list_movements(
    variant_id: UUID,
    session: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[StockMovementRead]:
    with errors():
        return [
            StockMovementRead.model_validate(item)
            for item in ProductStockService(session).movements(
                variant_id, offset, limit
            )
        ]


@router.get("/product-variants/{variant_id}/stock", response_model=ProductStockRead)
def get_stock(variant_id: UUID, session: DatabaseSession) -> ProductStockRead:
    with errors():
        return ProductStockService(session).stock(variant_id)
