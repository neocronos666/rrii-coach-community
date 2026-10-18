from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from app.modules.costing.exceptions import CurrencyMismatchError

MONEY_QUANTUM = Decimal("0.0001")
UNIT_COST_QUANTUM = Decimal("0.00000001")


def monetary_snapshot(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def unit_cost_snapshot(value: Decimal) -> Decimal:
    return value.quantize(UNIT_COST_QUANTUM, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: str

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise CurrencyMismatchError(
                f"No se puede sumar {self.currency} con {other.currency}"
            )
        return Money(self.amount + other.amount, self.currency)


@dataclass(frozen=True, slots=True)
class CostQuote:
    amount: Decimal
    currency: str
    unit: str
    source: str
    source_reference: str | None
    as_of: datetime


@dataclass(frozen=True, slots=True)
class ResolvedCostItem:
    category: str
    description: str
    quantity: Decimal
    unit: str
    unit_cost: Decimal | None
    currency: str | None
    source: str
    source_reference: str | None = None
    warning: str | None = None


@dataclass(frozen=True, slots=True)
class CalculatedCostLine:
    category: str
    description: str
    quantity: Decimal
    unit: str
    unit_cost: Decimal | None
    currency: str | None
    subtotal: Decimal | None
    source: str
    source_reference: str | None
    complete: bool


@dataclass(frozen=True, slots=True)
class CalculatedBreakdown:
    lines: tuple[CalculatedCostLine, ...]
    totals_by_currency: dict[str, Decimal]
    complete: bool
    multi_currency: bool
    warnings: tuple[str, ...]
