from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.db.session import get_db_session
from app.modules.orders.exceptions import (
    OrderNotCancellableError,
    OrderNotFoundError,
)
from app.modules.orders.models import Order
from app.modules.orders.schemas import OrderRead
from app.modules.orders.service import OrderService
from app.modules.orders.types import OrderStatus

router = APIRouter(prefix="/orders", tags=["orders"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]


@router.get("", response_model=list[OrderRead], summary="Listar pedidos")
def list_orders(
    session: DatabaseSession,
    order_status: Annotated[OrderStatus | None, Query(alias="status")] = None,
) -> list[Order]:
    return OrderService(session).list(order_status)


@router.get(
    "/{order_id}",
    response_model=OrderRead,
    summary="Consultar pedido",
    responses={404: {"description": "Pedido inexistente"}},
)
def get_order(order_id: UUID, session: DatabaseSession) -> Order:
    try:
        return OrderService(session).get(order_id)
    except OrderNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/{order_id}/cancel",
    response_model=OrderRead,
    summary="Cancelar pedido pendiente",
    responses={
        404: {"description": "Pedido inexistente"},
        409: {"description": "Estado inválido"},
    },
)
def cancel_order(order_id: UUID, session: DatabaseSession) -> Order:
    try:
        return OrderService(session).cancel(order_id)
    except OrderNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
        ) from error
    except OrderNotCancellableError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(error)
        ) from error
    except PersistenceError as error:
        raise HTTPException(
            status_code=500, detail="No se pudo cancelar el pedido"
        ) from error
