from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.modules.quotes.conversion_models import QuoteConversion


class QuoteConversionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, conversion: QuoteConversion) -> QuoteConversion:
        self._session.add(conversion)
        self._session.flush()
        return conversion

    def get_by_quote(self, quote_id: UUID) -> QuoteConversion | None:
        statement = (
            select(QuoteConversion)
            .options(
                joinedload(QuoteConversion.order),
                joinedload(QuoteConversion.project),
            )
            .where(QuoteConversion.quote_id == quote_id)
        )
        return self._session.scalar(statement)
