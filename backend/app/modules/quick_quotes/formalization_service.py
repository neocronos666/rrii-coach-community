import logging
from decimal import Decimal, localcontext
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.modules.costing.models import CostCalculation, CostCalculationLine
from app.modules.quick_quotes.exceptions import (
    QuickQuoteConflictError,
    QuickQuoteNotFoundError,
)
from app.modules.quick_quotes.formalization_models import QuickQuoteFormalization
from app.modules.quick_quotes.formalization_schemas import (
    QuickQuoteFormalizationRead,
    QuickQuoteFormalize,
)
from app.modules.quick_quotes.models import QuickQuote, QuickQuoteRevision
from app.modules.quick_quotes.service import QuickQuoteService
from app.modules.quotes.exceptions import (
    IncompleteCostCalculationError,
    InvalidQuoteAdjustmentError,
    MultiCurrencyQuoteUnsupportedError,
)
from app.modules.quotes.schemas import QuoteCreate, QuoteItemInput
from app.modules.quotes.service import QuoteService

logger = logging.getLogger(__name__)


class QuickQuoteFormalizationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _read(self, row: QuickQuoteFormalization) -> QuickQuoteFormalizationRead:
        source = self.session.get(QuickQuoteRevision, row.source_revision_id)
        assert source is not None
        return QuickQuoteFormalizationRead(
            quick_quote_id=row.quick_quote_id,
            source_revision_id=row.source_revision_id,
            source_revision=source.revision,
            quote_id=row.quote_id,
            cost_calculation_id=row.cost_calculation_id,
            request_id=row.request_id,
            created_at=row.created_at,
        )

    def get(self, quote_id: UUID) -> QuickQuoteFormalizationRead:
        row = self.session.scalar(
            select(QuickQuoteFormalization).where(
                QuickQuoteFormalization.quick_quote_id == quote_id
            )
        )
        if row is None:
            raise QuickQuoteNotFoundError("El borrador no tiene un Quote formal")
        return self._read(row)

    def formalize(
        self, quote_id: UUID, payload: QuickQuoteFormalize
    ) -> QuickQuoteFormalizationRead:
        for attempt in range(3):
            try:
                self.session.execute(
                    text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                )
                prior = self.session.scalar(
                    select(QuickQuoteFormalization).where(
                        QuickQuoteFormalization.request_id == payload.request_id
                    )
                )
                if prior is not None:
                    if (
                        prior.quick_quote_id != quote_id
                        or QuickQuoteFormalize.model_validate(prior.request_payload)
                        != payload
                    ):
                        raise QuickQuoteConflictError(
                            "request_id ya corresponde a otra formalización"
                        )
                    result = self._read(prior)
                    self.session.commit()
                    return result
                root = self.session.scalar(
                    select(QuickQuote)
                    .where(QuickQuote.id == quote_id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
                if root is None:
                    raise QuickQuoteNotFoundError("No existe el borrador")
                existing = self.session.scalar(
                    select(QuickQuoteFormalization.id).where(
                        QuickQuoteFormalization.quick_quote_id == quote_id
                    )
                )
                if existing is not None:
                    raise QuickQuoteConflictError(
                        "El borrador ya tiene un Quote formal; consultar su vínculo"
                    )
                row = self.session.scalar(
                    select(QuickQuoteRevision).where(
                        QuickQuoteRevision.quick_quote_id == quote_id,
                        QuickQuoteRevision.revision == payload.source_revision,
                    )
                )
                if row is None:
                    raise QuickQuoteNotFoundError("No existe la revisión elegida")
                saved = QuickQuoteService.read(row)
                preview = saved.evaluation.preview
                if not preview.complete or preview.markup_percentage is None:
                    raise IncompleteCostCalculationError(
                        "Se requiere costo completo y markup definido en la revisión"
                    )
                if preview.multi_currency or len(preview.totals_by_currency) != 1:
                    raise MultiCurrencyQuoteUnsupportedError(
                        "La revisión debe tener exactamente una moneda"
                    )
                if any(
                    value > Decimal("99999999999999.9999")
                    for value in preview.totals_by_currency.values()
                ):
                    raise InvalidQuoteAdjustmentError(
                        "El costo excede el rango comercial"
                    )
                for line in preview.lines:
                    if line.quantity > Decimal("999999999999.999999") or (
                        line.unit_cost is not None
                        and line.unit_cost > Decimal("9999999999999999.99999999")
                    ):
                        raise InvalidQuoteAdjustmentError(
                            "Una línea excede la precisión persistente"
                        )
                calculation = CostCalculation(
                    calculation_type="recipe_demand",
                    demand_quantity=preview.target_quantity,
                    demand_unit=saved.evaluation.variant_unit,
                    complete=True,
                    multi_currency=False,
                    warnings=preview.warnings,
                    calculated_at=row.created_at,
                )
                calculation.lines = [
                    CostCalculationLine(
                        position=index,
                        category=line.category,
                        description=line.description,
                        quantity=line.quantity,
                        unit=line.unit,
                        unit_cost=line.unit_cost,
                        currency=line.currency,
                        subtotal=line.subtotal,
                        source=line.source,
                        source_reference=line.source_reference,
                        complete=line.complete,
                    )
                    for index, line in enumerate(preview.lines)
                ]
                self.session.add(calculation)
                self.session.flush()
                try:
                    quote_input = QuoteCreate(
                        title=payload.title or saved.definition.title,
                        markup_percentage=preview.markup_percentage,
                        valid_until=payload.valid_until,
                        adjustments=payload.adjustments,
                        final_price=payload.final_price,
                        notes=saved.definition.notes,
                        items=[
                            QuoteItemInput(
                                cost_calculation_id=calculation.id,
                                description=saved.definition.title,
                                quantity=preview.target_quantity,
                            )
                        ],
                    )
                except ValidationError as error:
                    raise InvalidQuoteAdjustmentError(
                        "La revisión excede los límites del contrato comercial"
                    ) from error
                with localcontext() as context:
                    context.prec = 60
                    formal = QuoteService(self.session).create_in_transaction(
                        quote_input, demand_calculation_id=calculation.id
                    )
                bridge = QuickQuoteFormalization(
                    quick_quote_id=quote_id,
                    source_revision_id=row.id,
                    quote_id=formal.id,
                    cost_calculation_id=calculation.id,
                    request_id=payload.request_id,
                    request_payload=payload.model_dump(mode="json"),
                )
                self.session.add(bridge)
                self.session.flush()
                result = self._read(bridge)
                self.session.commit()
                return result
            except SQLAlchemyError as error:
                self.session.rollback()
                state = (
                    getattr(error.orig, "sqlstate", None)
                    if isinstance(error, DBAPIError)
                    else None
                )
                constraint = (
                    getattr(
                        getattr(getattr(error, "orig", None), "diag", None),
                        "constraint_name",
                        "",
                    )
                    or ""
                )
                retryable = state in {"40001", "40P01"} or (
                    state == "23505"
                    and constraint.startswith("uq_quick_quote_formalizations_")
                )
                if retryable and attempt < 2:
                    continue
                if retryable:
                    raise QuickQuoteConflictError(
                        "Conflicto concurrente; reintentar con el mismo request_id"
                    ) from error
                logger.error(
                    "quick_quote_formalization_failed (%s)", type(error).__name__
                )
                raise PersistenceError("No se pudo formalizar el borrador") from error
            except Exception:
                self.session.rollback()
                raise
        raise AssertionError("Reintentos agotados")
