from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class QuoteStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class AdjustmentType(StrEnum):
    SURCHARGE = "surcharge"
    DISCOUNT = "discount"


class AdjustmentValueType(StrEnum):
    FIXED = "fixed"
    PERCENTAGE = "percentage"


@dataclass(frozen=True, slots=True)
class AdjustmentSpec:
    description: str
    adjustment_type: AdjustmentType
    value_type: AdjustmentValueType
    value: Decimal


@dataclass(frozen=True, slots=True)
class CalculatedAdjustment:
    description: str
    adjustment_type: AdjustmentType
    value_type: AdjustmentValueType
    value: Decimal
    amount: Decimal


@dataclass(frozen=True, slots=True)
class CalculatedQuote:
    technical_cost: Decimal
    markup_percentage: Decimal
    markup_amount: Decimal
    subtotal_after_markup: Decimal
    adjustments: tuple[CalculatedAdjustment, ...]
    suggested_price: Decimal
