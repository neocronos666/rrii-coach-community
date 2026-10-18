from uuid import UUID

from sqlalchemy import Sequence, extract, select
from sqlalchemy.orm import Session, selectinload

from app.modules.quotes.models import Quote

quote_code_sequence = Sequence("quote_code_sequence")


class QuoteRepository:
    """Persistencia específica; la transacción pertenece al servicio."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def next_code(self, year: int) -> str:
        number = self._session.scalar(quote_code_sequence.next_value())
        if number is None:
            raise RuntimeError("No se pudo generar el código de presupuesto")
        return f"Q-{year}-{number:06d}"

    def add(self, quote: Quote) -> Quote:
        self._session.add(quote)
        self._session.flush()
        return quote

    def get(self, quote_id: UUID) -> Quote | None:
        statement = (
            select(Quote)
            .options(selectinload(Quote.items), selectinload(Quote.adjustments))
            .where(Quote.id == quote_id)
        )
        return self._session.scalar(statement)

    def get_for_update(self, quote_id: UUID) -> Quote | None:
        statement = (
            select(Quote)
            .options(selectinload(Quote.items), selectinload(Quote.adjustments))
            .where(Quote.id == quote_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return self._session.scalar(statement)

    def list(self, *, year: int | None = None) -> list[Quote]:
        statement = select(Quote).options(
            selectinload(Quote.items), selectinload(Quote.adjustments)
        )
        if year is not None:
            statement = statement.where(extract("year", Quote.created_at) == year)
        statement = statement.order_by(Quote.created_at.desc())
        return list(self._session.scalars(statement))

    def delete_children(self, quote: Quote) -> None:
        quote.items.clear()
        quote.adjustments.clear()
        self._session.flush()
