from decimal import ROUND_FLOOR, Decimal

from app.modules.costing.types import monetary_snapshot
from app.modules.installation.schemas import DepositPolicy, DepositType
from app.modules.quotes.exceptions import (
    InvalidDepositError,
    InvalidQuoteAdjustmentError,
)
from app.modules.quotes.types import (
    AdjustmentSpec,
    AdjustmentType,
    AdjustmentValueType,
    CalculatedAdjustment,
    CalculatedQuote,
)

ONE_HUNDRED = Decimal(100)


class QuoteCalculator:
    """Aritmética comercial pura, sin dependencias de API o persistencia."""

    def calculate(
        self,
        technical_cost: Decimal,
        markup_percentage: Decimal,
        adjustments: list[AdjustmentSpec],
    ) -> CalculatedQuote:
        if technical_cost < 0 or markup_percentage < 0:
            raise InvalidQuoteAdjustmentError("Costo y markup deben ser positivos")
        technical = monetary_snapshot(technical_cost)
        markup_amount = monetary_snapshot(technical * markup_percentage / ONE_HUNDRED)
        subtotal = monetary_snapshot(technical + markup_amount)
        calculated: list[CalculatedAdjustment] = []
        signed_total = Decimal(0)
        for adjustment in adjustments:
            if adjustment.value < 0:
                raise InvalidQuoteAdjustmentError(
                    "Los valores de ajustes no pueden ser negativos"
                )
            amount = (
                subtotal * adjustment.value / ONE_HUNDRED
                if adjustment.value_type is AdjustmentValueType.PERCENTAGE
                else adjustment.value
            )
            amount = monetary_snapshot(amount)
            signed_total += (
                amount
                if adjustment.adjustment_type is AdjustmentType.SURCHARGE
                else -amount
            )
            calculated.append(
                CalculatedAdjustment(
                    description=adjustment.description,
                    adjustment_type=adjustment.adjustment_type,
                    value_type=adjustment.value_type,
                    value=adjustment.value,
                    amount=amount,
                )
            )
        suggested = monetary_snapshot(subtotal + signed_total)
        if suggested < 0:
            raise InvalidQuoteAdjustmentError(
                "Los ajustes no pueden producir un precio negativo"
            )
        return CalculatedQuote(
            technical_cost=technical,
            markup_percentage=markup_percentage,
            markup_amount=markup_amount,
            subtotal_after_markup=subtotal,
            adjustments=tuple(calculated),
            suggested_price=suggested,
        )

    @staticmethod
    def round_final_price(amount: Decimal, currency: str) -> Decimal:
        """Política comercial: total ARS al peso inferior, sin alterar costos."""
        if currency == "ARS":
            return monetary_snapshot(
                amount.quantize(Decimal("1"), rounding=ROUND_FLOOR)
            )
        return amount

    def calculate_deposit(
        self,
        final_price: Decimal,
        policy: DepositPolicy,
        deposit_type: DepositType | None,
        deposit_value: Decimal | None,
    ) -> Decimal | None:
        if policy is DepositPolicy.NONE:
            return None
        if deposit_type is None or deposit_value is None:
            raise InvalidDepositError("La política de seña está incompleta")
        if deposit_type is DepositType.PERCENTAGE:
            if deposit_value > ONE_HUNDRED:
                raise InvalidDepositError("La seña porcentual supera el 100%")
            return monetary_snapshot(final_price * deposit_value / ONE_HUNDRED)
        if deposit_value > final_price:
            raise InvalidDepositError("La seña fija supera el precio final")
        return monetary_snapshot(deposit_value)
