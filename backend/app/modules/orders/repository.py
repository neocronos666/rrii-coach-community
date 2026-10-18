from uuid import UUID

from sqlalchemy import Sequence, select
from sqlalchemy.orm import Session

from app.modules.orders.models import Order
from app.modules.orders.types import OrderStatus

order_code_sequence = Sequence("order_code_sequence")


class OrderRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def next_code(self, year: int) -> str:
        number = self._session.scalar(order_code_sequence.next_value())
        if number is None:
            raise RuntimeError("No se pudo generar el código de pedido")
        return f"O-{year}-{number:06d}"

    def add(self, order: Order) -> Order:
        self._session.add(order)
        self._session.flush()
        return order

    def get(self, order_id: UUID) -> Order | None:
        return self._session.get(Order, order_id)

    def list(self, status: OrderStatus | None = None) -> list[Order]:
        statement = select(Order).order_by(Order.created_at.desc(), Order.id)
        if status is not None:
            statement = statement.where(Order.status == status.value)
        return list(self._session.scalars(statement))
