import logging
from typing import Literal, cast
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.modules.costing.preview_schemas import PricingEvaluation
from app.modules.costing.preview_service import PricingPreviewService
from app.modules.quick_quotes.exceptions import (
    QuickQuoteConflictError,
    QuickQuoteNotFoundError,
)
from app.modules.quick_quotes.models import QuickQuote, QuickQuoteRevision
from app.modules.quick_quotes.schemas import (
    QuickQuoteCreate,
    QuickQuoteDefinition,
    QuickQuoteRead,
    QuickQuoteRecalculate,
    QuickQuoteReplace,
)

logger = logging.getLogger(__name__)
WriteRequest = QuickQuoteCreate | QuickQuoteReplace | QuickQuoteRecalculate
Operation = Literal["create", "replace", "recalculate"]


class QuickQuoteService:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def read(row: QuickQuoteRevision) -> QuickQuoteRead:
        return QuickQuoteRead(
            id=row.quick_quote_id,
            revision=row.revision,
            request_id=row.request_id,
            operation=cast(Operation, row.operation),
            definition=QuickQuoteDefinition.model_validate(row.definition),
            evaluation=PricingEvaluation.model_validate(row.evaluation),
            created_at=row.created_at,
        )

    def get(self, quote_id: UUID, revision: int | None = None) -> QuickQuoteRead:
        statement = (
            select(QuickQuoteRevision)
            .join(QuickQuote, QuickQuote.id == QuickQuoteRevision.quick_quote_id)
            .where(QuickQuote.id == quote_id)
        )
        if revision is None:
            statement = statement.where(
                QuickQuoteRevision.revision == QuickQuote.current_revision
            )
        else:
            statement = statement.where(QuickQuoteRevision.revision == revision)
        row = self.session.scalar(statement)
        if row is None:
            raise QuickQuoteNotFoundError("No existe el borrador o la revisión")
        return self.read(row)

    def list_quotes(self, limit: int, offset: int) -> list[QuickQuoteRead]:
        rows = self.session.scalars(
            select(QuickQuoteRevision)
            .join(QuickQuote, QuickQuote.id == QuickQuoteRevision.quick_quote_id)
            .where(QuickQuoteRevision.revision == QuickQuote.current_revision)
            .order_by(QuickQuote.created_at.desc(), QuickQuote.id)
            .limit(limit)
            .offset(offset)
        )
        return [self.read(row) for row in rows]

    def history(self, quote_id: UUID, limit: int, offset: int) -> list[QuickQuoteRead]:
        self.get(quote_id)
        rows = self.session.scalars(
            select(QuickQuoteRevision)
            .where(QuickQuoteRevision.quick_quote_id == quote_id)
            .order_by(QuickQuoteRevision.revision.desc())
            .limit(limit)
            .offset(offset)
        )
        return [self.read(row) for row in rows]

    def create(self, payload: QuickQuoteCreate) -> QuickQuoteRead:
        return self._write("create", None, payload)

    def replace(self, quote_id: UUID, payload: QuickQuoteReplace) -> QuickQuoteRead:
        return self._write("replace", quote_id, payload)

    def recalculate(
        self, quote_id: UUID, payload: QuickQuoteRecalculate
    ) -> QuickQuoteRead:
        return self._write("recalculate", quote_id, payload)

    def _write(
        self, operation: Operation, quote_id: UUID | None, payload: WriteRequest
    ) -> QuickQuoteRead:
        for attempt in range(3):
            try:
                self.session.execute(
                    text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                )
                previous = self.session.scalar(
                    select(QuickQuoteRevision).where(
                        QuickQuoteRevision.request_id == payload.request_id
                    )
                )
                if previous is not None:
                    if (
                        previous.operation != operation
                        or (
                            quote_id is not None and previous.quick_quote_id != quote_id
                        )
                        or type(payload).model_validate(previous.request_payload)
                        != payload
                    ):
                        raise QuickQuoteConflictError(
                            "request_id ya corresponde a otra operación"
                        )
                    result = self.read(previous)
                    self.session.commit()
                    return result
                if quote_id is None:
                    item = QuickQuote(current_revision=1)
                else:
                    existing = self.session.scalar(
                        select(QuickQuote)
                        .where(QuickQuote.id == quote_id)
                        .with_for_update()
                        .execution_options(populate_existing=True)
                    )
                    if existing is None:
                        raise QuickQuoteNotFoundError(
                            "No existe el borrador solicitado"
                        )
                    item = existing
                    assert isinstance(
                        payload, QuickQuoteReplace | QuickQuoteRecalculate
                    )
                    if item.current_revision != payload.expected_revision:
                        raise QuickQuoteConflictError(
                            "La revisión cambió; consultar el borrador antes de editar"
                        )
                if isinstance(payload, QuickQuoteRecalculate):
                    definition = self.get(item.id).definition
                else:
                    definition = QuickQuoteDefinition(
                        title=payload.title,
                        notes=payload.notes,
                        pricing=payload.pricing,
                    )
                evaluation = PricingPreviewService(self.session).evaluate_in_snapshot(
                    definition.pricing
                )
                if quote_id is None:
                    self.session.add(item)
                else:
                    item.current_revision += 1
                self.session.flush()
                row = QuickQuoteRevision(
                    quick_quote_id=item.id,
                    revision=item.current_revision,
                    request_id=payload.request_id,
                    operation=operation,
                    request_payload=payload.model_dump(mode="json"),
                    definition=definition.model_dump(mode="json"),
                    evaluation=evaluation.model_dump(mode="json"),
                    recipe_id=definition.pricing.recipe_id,
                    variant_id=definition.pricing.variant_id,
                )
                self.session.add(row)
                self.session.flush()
                result = self.read(row)
                self.session.commit()
                return result
            except SQLAlchemyError as error:
                self.session.rollback()
                state = (
                    getattr(error.orig, "sqlstate", None)
                    if isinstance(error, DBAPIError)
                    else None
                )
                constraint = getattr(
                    getattr(getattr(error, "orig", None), "diag", None),
                    "constraint_name",
                    None,
                )
                retryable = state in {"40001", "40P01"} or (
                    state == "23505"
                    and constraint == "uq_quick_quote_revisions_request_id"
                )
                if retryable and attempt < 2:
                    continue
                if retryable:
                    raise QuickQuoteConflictError(
                        "Conflicto concurrente; reintentar con el mismo request_id"
                    ) from error
                logger.error("quick_quote_write_failed (%s)", type(error).__name__)
                raise PersistenceError("No se pudo guardar el borrador") from error
            except Exception:
                self.session.rollback()
                raise
        raise AssertionError("Reintentos agotados")
