import logging
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.modules.costing.models import CostCalculation
from app.modules.costing.repository import CostCalculationRepository
from app.modules.costing.types import monetary_snapshot
from app.modules.installation.schemas import DepositPolicy, DepositType
from app.modules.installation.service import InstallationSettingsService
from app.modules.quick_quotes.formalization_models import QuickQuoteFormalization
from app.modules.quick_quotes.models import QuickQuoteRevision
from app.modules.quotes.calculator import QuoteCalculator
from app.modules.quotes.exceptions import (
    IncompleteCostCalculationError,
    InvalidQuoteAdjustmentError,
    InvalidQuoteTransitionError,
    MultiCurrencyQuoteUnsupportedError,
    QuoteNotEditableError,
    QuoteNotFoundError,
)
from app.modules.quotes.models import Quote, QuoteAdjustment, QuoteItem
from app.modules.quotes.repository import QuoteRepository
from app.modules.quotes.schemas import (
    QuoteAdjustmentInput,
    QuoteAdjustmentRead,
    QuoteBreakdown,
    QuoteCreate,
    QuoteItemInput,
    QuoteItemRead,
    QuoteRead,
    QuoteUpdate,
)
from app.modules.quotes.types import AdjustmentSpec, CalculatedAdjustment, QuoteStatus

logger = logging.getLogger(__name__)


class QuoteService:
    def __init__(
        self,
        session: Session,
        repository: QuoteRepository | None = None,
        calculator: QuoteCalculator | None = None,
    ) -> None:
        self._session = session
        self._quotes = repository or QuoteRepository(session)
        self._costs = CostCalculationRepository(session)
        self._settings = InstallationSettingsService(session)
        self._calculator = calculator or QuoteCalculator()

    def create(self, payload: QuoteCreate) -> QuoteRead:
        try:
            quote = self.create_in_transaction(payload)
            self._session.commit()
            logger.info("quote_created quote_id=%s code=%s", quote.id, quote.code)
            if quote.final_price_overridden:
                logger.info("quote_final_price_overridden quote_id=%s", quote.id)
            return self._to_read(quote)
        except SQLAlchemyError as error:
            self._session.rollback()
            logger.error(
                "quote_create_failed (%s); rollback ejecutado", type(error).__name__
            )
            raise PersistenceError("No se pudo guardar el presupuesto") from error

    def create_in_transaction(
        self, payload: QuoteCreate, *, demand_calculation_id: UUID | None = None
    ) -> Quote:
        """Construye el snapshot; la transacción y confirmación pertenecen al caller."""
        settings = self._settings.get()
        items, currency = self._resolve_items(
            payload.items, demand_calculation_id=demand_calculation_id
        )
        markup = (
            payload.markup_percentage
            if payload.markup_percentage is not None
            else settings.default_markup_percentage or Decimal(0)
        )
        result = self._calculator.calculate(
            sum((item.technical_total_cost for item in items), Decimal(0)),
            markup,
            self._adjustment_specs(payload.adjustments),
        )
        final_price = (
            monetary_snapshot(payload.final_price)
            if payload.final_price is not None
            else result.suggested_price
        )
        final_price = self._calculator.round_final_price(final_price, currency)
        deposit_amount = self._calculator.calculate_deposit(
            final_price,
            settings.deposit_policy,
            settings.deposit_type,
            settings.deposit_value,
        )
        if demand_calculation_id is not None:
            amounts = [
                result.technical_cost,
                result.markup_amount,
                result.subtotal_after_markup,
                result.suggested_price,
                final_price,
            ]
            amounts.extend(item.technical_unit_cost for item in items)
            amounts.extend(adjustment.amount for adjustment in result.adjustments)
            if deposit_amount is not None:
                amounts.append(deposit_amount)
            if any(amount > Decimal("99999999999999.9999") for amount in amounts):
                raise InvalidQuoteAdjustmentError(
                    "El importe excede el rango comercial"
                )
        quote = Quote(
            code=self._quotes.next_code(datetime.now(UTC).year),
            title=payload.title,
            description=payload.description,
            status=QuoteStatus.DRAFT.value,
            currency=currency,
            technical_cost_total=result.technical_cost,
            markup_percentage=result.markup_percentage,
            markup_amount=result.markup_amount,
            subtotal_after_markup=result.subtotal_after_markup,
            suggested_price=result.suggested_price,
            final_price=final_price,
            final_price_overridden=payload.final_price is not None,
            valid_until=payload.valid_until,
            deposit_policy=settings.deposit_policy.value,
            deposit_type=settings.deposit_type.value if settings.deposit_type else None,
            deposit_value=settings.deposit_value,
            deposit_amount=deposit_amount,
            notes=payload.notes,
            items=items,
            adjustments=self._build_adjustments(result.adjustments),
        )
        self._quotes.add(quote)
        self._expire_if_needed(quote, commit=False)
        return quote

    def get(self, quote_id: UUID) -> QuoteRead:
        quote = self._get_model(quote_id)
        self._expire_if_needed(quote)
        return self._to_read(quote)

    def list_quotes(
        self, *, status: QuoteStatus | None = None, year: int | None = None
    ) -> list[QuoteRead]:
        quotes = self._quotes.list(year=year)
        changed = False
        for quote in quotes:
            changed = self._expire_if_needed(quote, commit=False) or changed
        if changed:
            self._session.commit()
        if status is not None:
            quotes = [quote for quote in quotes if quote.status == status.value]
        return [self._to_read(quote) for quote in quotes]

    def update(self, quote_id: UUID, payload: QuoteUpdate) -> QuoteRead:
        quote = self._get_model(quote_id, lock=True)
        self._expire_if_needed(quote)
        self._ensure_editable(quote)
        try:
            fields = payload.model_fields_set
            bridge = self._session.scalar(
                select(QuickQuoteFormalization).where(
                    QuickQuoteFormalization.quote_id == quote.id
                )
            )
            if (
                bridge is not None
                and payload.items is not None
                and payload.items != self._item_inputs(quote)
            ):
                raise QuoteNotEditableError(
                    "Los items técnicos formalizados conservan cantidad y origen"
                )
            item_inputs = (
                payload.items if payload.items is not None else self._item_inputs(quote)
            )
            adjustment_inputs = (
                payload.adjustments
                if payload.adjustments is not None
                else self._adjustment_inputs(quote)
            )
            items, currency = self._resolve_items(
                item_inputs,
                demand_calculation_id=bridge.cost_calculation_id if bridge else None,
            )
            markup = (
                payload.markup_percentage
                if "markup_percentage" in fields
                and payload.markup_percentage is not None
                else quote.markup_percentage
            )
            result = self._calculator.calculate(
                sum((item.technical_total_cost for item in items), Decimal(0)),
                markup,
                self._adjustment_specs(adjustment_inputs),
            )
            if "final_price" in fields:
                overridden = payload.final_price is not None
                final_price = (
                    monetary_snapshot(payload.final_price)
                    if payload.final_price is not None
                    else result.suggested_price
                )
            elif quote.final_price_overridden:
                overridden = True
                final_price = quote.final_price
            else:
                overridden = False
                final_price = result.suggested_price
            pricing_fields = {
                "items",
                "adjustments",
                "markup_percentage",
                "final_price",
            }
            if fields & pricing_fields:
                final_price = self._calculator.round_final_price(final_price, currency)
            else:
                # Editar textos no reinterpreta precios de presupuestos históricos.
                final_price = quote.final_price
            deposit_amount = self._calculator.calculate_deposit(
                final_price,
                DepositPolicy(quote.deposit_policy),
                DepositType(quote.deposit_type) if quote.deposit_type else None,
                quote.deposit_value,
            )
            quote.items.clear()
            quote.adjustments.clear()
            self._session.flush()
            quote.items = items
            quote.adjustments = self._build_adjustments(result.adjustments)
            quote.currency = currency
            quote.technical_cost_total = result.technical_cost
            quote.markup_percentage = result.markup_percentage
            quote.markup_amount = result.markup_amount
            quote.subtotal_after_markup = result.subtotal_after_markup
            quote.suggested_price = result.suggested_price
            quote.final_price = final_price
            quote.final_price_overridden = overridden
            quote.deposit_amount = deposit_amount
            quote.updated_at = datetime.now(UTC)
            for name in ("title", "description", "valid_until", "notes"):
                if name in fields:
                    setattr(quote, name, getattr(payload, name))
            self._session.commit()
            logger.info("quote_updated quote_id=%s", quote.id)
            if overridden:
                logger.info("quote_final_price_overridden quote_id=%s", quote.id)
            return self._to_read(quote)
        except SQLAlchemyError as error:
            self._session.rollback()
            raise PersistenceError("No se pudo actualizar el presupuesto") from error

    def approve(self, quote_id: UUID) -> QuoteRead:
        quote = self._get_model(quote_id, lock=True)
        self._expire_if_needed(quote)
        if quote.status != QuoteStatus.DRAFT.value:
            raise InvalidQuoteTransitionError(
                "Solo un presupuesto draft puede aprobarse"
            )
        quote.status = QuoteStatus.APPROVED.value
        quote.approved_at = datetime.now(UTC)
        self._session.commit()
        logger.info("quote_approved quote_id=%s", quote.id)
        return self._to_read(quote)

    def reject(self, quote_id: UUID, reason: str | None) -> QuoteRead:
        quote = self._get_model(quote_id, lock=True)
        self._expire_if_needed(quote)
        if quote.status != QuoteStatus.DRAFT.value:
            raise InvalidQuoteTransitionError(
                "Solo un presupuesto draft puede rechazarse"
            )
        quote.status = QuoteStatus.REJECTED.value
        quote.rejected_at = datetime.now(UTC)
        quote.rejection_reason = reason
        self._session.commit()
        logger.info("quote_rejected quote_id=%s", quote.id)
        return self._to_read(quote)

    def _resolve_items(
        self, inputs: list[QuoteItemInput], *, demand_calculation_id: UUID | None = None
    ) -> tuple[list[QuoteItem], str]:
        items: list[QuoteItem] = []
        currencies: set[str] = set()
        for position, item_input in enumerate(inputs):
            calculation = self._costs.get(item_input.cost_calculation_id)
            if calculation is None:
                raise QuoteNotFoundError("No existe el cálculo técnico solicitado")
            unit_cost, currency = self._cost_snapshot(calculation)
            if calculation.demand_quantity is not None:
                if calculation.id != demand_calculation_id:
                    raise IncompleteCostCalculationError(
                        "El cálculo de demanda requiere su puente de origen"
                    )
                if item_input.quantity != calculation.demand_quantity:
                    raise IncompleteCostCalculationError(
                        "La demanda requiere otra evaluación para cambiar cantidad"
                    )
                total_cost = unit_cost
                unit_cost = monetary_snapshot(total_cost / calculation.demand_quantity)
            else:
                total_cost = monetary_snapshot(unit_cost * item_input.quantity)
            currencies.add(currency)
            items.append(
                QuoteItem(
                    description=item_input.description,
                    quantity=item_input.quantity,
                    cost_calculation_id=calculation.id,
                    technical_unit_cost=unit_cost,
                    technical_total_cost=total_cost,
                    currency=currency,
                    position=position,
                    notes=item_input.notes,
                )
            )
        if len(currencies) != 1:
            raise MultiCurrencyQuoteUnsupportedError(
                "Todos los elementos deben utilizar la misma moneda"
            )
        return items, currencies.pop()

    def _cost_snapshot(self, calculation: CostCalculation) -> tuple[Decimal, str]:
        if not calculation.complete:
            raise IncompleteCostCalculationError(
                "No se puede presupuestar un cálculo técnico incompleto"
            )
        if calculation.multi_currency:
            raise MultiCurrencyQuoteUnsupportedError(
                "Community no admite presupuestos multimoneda"
            )
        totals: dict[str, Decimal] = {}
        for line in calculation.lines:
            if line.currency is not None and line.subtotal is not None:
                totals[line.currency] = (
                    totals.get(line.currency, Decimal(0)) + line.subtotal
                )
        if len(totals) != 1:
            raise IncompleteCostCalculationError(
                "El cálculo técnico no posee un total monetario único"
            )
        currency, total = next(iter(totals.items()))
        return monetary_snapshot(total), currency

    @staticmethod
    def _adjustment_specs(inputs: list[QuoteAdjustmentInput]) -> list[AdjustmentSpec]:
        return [
            AdjustmentSpec(
                item.description, item.adjustment_type, item.value_type, item.value
            )
            for item in inputs
        ]

    @staticmethod
    def _build_adjustments(
        calculated: tuple[CalculatedAdjustment, ...],
    ) -> list[QuoteAdjustment]:
        result: list[QuoteAdjustment] = []
        for position, raw in enumerate(calculated):
            result.append(
                QuoteAdjustment(
                    description=raw.description,
                    adjustment_type=raw.adjustment_type.value,
                    value_type=raw.value_type.value,
                    value=raw.value,
                    amount=raw.amount,
                    position=position,
                )
            )
        return result

    @staticmethod
    def _item_inputs(quote: Quote) -> list[QuoteItemInput]:
        return [
            QuoteItemInput.model_validate(
                {
                    "cost_calculation_id": item.cost_calculation_id,
                    "description": item.description,
                    "quantity": item.quantity,
                    "notes": item.notes,
                }
            )
            for item in quote.items
        ]

    @staticmethod
    def _adjustment_inputs(quote: Quote) -> list[QuoteAdjustmentInput]:
        return [
            QuoteAdjustmentInput.model_validate(
                {
                    "description": item.description,
                    "adjustment_type": item.adjustment_type,
                    "value_type": item.value_type,
                    "value": item.value,
                }
            )
            for item in quote.adjustments
        ]

    def _get_model(self, quote_id: UUID, *, lock: bool = False) -> Quote:
        quote = (
            self._quotes.get_for_update(quote_id)
            if lock
            else self._quotes.get(quote_id)
        )
        if quote is None:
            raise QuoteNotFoundError("No existe el presupuesto solicitado")
        return quote

    @staticmethod
    def _ensure_editable(quote: Quote) -> None:
        if quote.status != QuoteStatus.DRAFT.value:
            raise QuoteNotEditableError("Solo un presupuesto draft puede editarse")

    def _expire_if_needed(self, quote: Quote, *, commit: bool = True) -> bool:
        if (
            quote.status == QuoteStatus.DRAFT.value
            and quote.valid_until is not None
            and quote.valid_until < date.today()
        ):
            quote.status = QuoteStatus.EXPIRED.value
            quote.expired_at = datetime.now(UTC)
            if commit:
                self._session.commit()
            logger.info("quote_expired quote_id=%s", quote.id)
            return True
        return False

    def _to_read(self, quote: Quote) -> QuoteRead:
        origin = self._session.execute(
            select(QuickQuoteFormalization.quick_quote_id, QuickQuoteRevision.revision)
            .join(
                QuickQuoteRevision,
                QuickQuoteRevision.id == QuickQuoteFormalization.source_revision_id,
            )
            .where(QuickQuoteFormalization.quote_id == quote.id)
        ).one_or_none()
        adjustments = [
            QuoteAdjustmentRead.model_validate(item) for item in quote.adjustments
        ]
        return QuoteRead(
            source_quick_quote_id=origin[0] if origin else None,
            source_quick_quote_revision=origin[1] if origin else None,
            id=quote.id,
            code=quote.code,
            title=quote.title,
            description=quote.description,
            status=QuoteStatus(quote.status),
            currency=quote.currency,
            final_price_overridden=quote.final_price_overridden,
            valid_until=quote.valid_until,
            deposit_policy=DepositPolicy(quote.deposit_policy),
            deposit_type=DepositType(quote.deposit_type)
            if quote.deposit_type
            else None,
            deposit_value=quote.deposit_value,
            notes=quote.notes,
            rejection_reason=quote.rejection_reason,
            items=[QuoteItemRead.model_validate(item) for item in quote.items],
            breakdown=QuoteBreakdown(
                technical_cost=quote.technical_cost_total,
                markup_percentage=quote.markup_percentage,
                markup_amount=quote.markup_amount,
                subtotal_after_markup=quote.subtotal_after_markup,
                adjustments=adjustments,
                suggested_price=quote.suggested_price,
                final_price=quote.final_price,
                deposit_amount=quote.deposit_amount,
            ),
            created_at=quote.created_at,
            updated_at=quote.updated_at,
            approved_at=quote.approved_at,
            rejected_at=quote.rejected_at,
            expired_at=quote.expired_at,
        )
