import logging
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.modules.orders.exceptions import (
    OrderNotCancellableError,
    OrderNotFoundError,
)
from app.modules.orders.models import Order
from app.modules.orders.repository import OrderRepository
from app.modules.orders.types import OrderStatus
from app.modules.products.allocation_repository import ProductAllocationRepository
from app.modules.supplies.reservation_repository import SupplyReservationRepository

logger = logging.getLogger(__name__)


class OrderService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._orders = OrderRepository(session)

    def list(self, status: OrderStatus | None = None) -> list[Order]:
        return self._orders.list(status)

    def get(self, order_id: UUID) -> Order:
        order = self._orders.get(order_id)
        if order is None:
            raise OrderNotFoundError("No existe el pedido solicitado")
        return order

    def cancel(self, order_id: UUID) -> Order:
        try:
            order = self.get(order_id)
            if order.status != OrderStatus.PENDING.value:
                raise OrderNotCancellableError(
                    "Solo un pedido pending puede cancelarse"
                )
            order.status = OrderStatus.CANCELLED.value
            self._session.flush()
            SupplyReservationRepository(self._session).release_order(order.id)
            ProductAllocationRepository(self._session).release_order(order.id)
            self._session.commit()
            logger.info("order_cancelled order_id=%s", order.id)
            return order
        except (OrderNotFoundError, OrderNotCancellableError):
            self._session.rollback()
            raise
        except SQLAlchemyError as error:
            self._session.rollback()
            raise PersistenceError("No se pudo cancelar el pedido") from error
