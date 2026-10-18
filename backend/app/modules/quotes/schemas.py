from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.validation import NonNegativeMoney
from app.modules.installation.schemas import DepositPolicy, DepositType
from app.modules.quotes.types import AdjustmentType, AdjustmentValueType, QuoteStatus

PositiveCommercialQuantity = Annotated[
    Decimal, Field(gt=0, max_digits=18, decimal_places=6)
]
NonNegativePercentage = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=4)]


class QuoteItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cost_calculation_id: UUID
    description: str = Field(min_length=1, max_length=1000)
    quantity: PositiveCommercialQuantity
    notes: str | None = None


class QuoteAdjustmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str = Field(min_length=1, max_length=1000)
    adjustment_type: AdjustmentType
    value_type: AdjustmentValueType
    value: NonNegativeMoney


class QuoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    markup_percentage: NonNegativePercentage | None = None
    valid_until: date | None = None
    items: list[QuoteItemInput] = Field(min_length=1)
    adjustments: list[QuoteAdjustmentInput] = Field(default_factory=list)
    final_price: NonNegativeMoney | None = Field(
        default=None,
        description="Total final propuesto; en ARS se guarda al peso inferior.",
    )
    notes: str | None = None


class QuoteUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    markup_percentage: NonNegativePercentage | None = None
    valid_until: date | None = None
    items: list[QuoteItemInput] | None = Field(default=None, min_length=1)
    adjustments: list[QuoteAdjustmentInput] | None = None
    final_price: NonNegativeMoney | None = Field(
        default=None,
        description="Total final propuesto; en ARS se guarda al peso inferior.",
    )
    notes: str | None = None

    @model_validator(mode="after")
    def reject_null_title(self) -> "QuoteUpdate":
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("title no puede ser null")
        return self


class QuoteReject(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str | None = None


class QuoteItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    description: str
    quantity: Decimal
    cost_calculation_id: UUID
    technical_unit_cost: Decimal
    technical_total_cost: Decimal
    currency: str
    position: int
    notes: str | None
    created_at: datetime


class QuoteAdjustmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    description: str
    adjustment_type: AdjustmentType
    value_type: AdjustmentValueType
    value: Decimal
    amount: Decimal
    position: int
    created_at: datetime


class QuoteBreakdown(BaseModel):
    technical_cost: Decimal
    markup_percentage: Decimal
    markup_amount: Decimal
    subtotal_after_markup: Decimal
    adjustments: list[QuoteAdjustmentRead]
    suggested_price: Decimal
    final_price: Decimal
    deposit_amount: Decimal | None


class QuoteRead(BaseModel):
    source_quick_quote_id: UUID | None = None
    source_quick_quote_revision: int | None = None
    id: UUID
    code: str
    title: str
    description: str | None
    status: QuoteStatus
    currency: str
    final_price_overridden: bool
    valid_until: date | None
    deposit_policy: DepositPolicy
    deposit_type: DepositType | None
    deposit_value: Decimal | None
    notes: str | None
    rejection_reason: str | None
    items: list[QuoteItemRead]
    breakdown: QuoteBreakdown
    created_at: datetime
    updated_at: datetime
    approved_at: datetime | None
    rejected_at: datetime | None
    expired_at: datetime | None
