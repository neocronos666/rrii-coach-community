from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.validation import NonNegativeMoney
from app.modules.products.schemas import Name
from app.modules.quotes.schemas import QuoteAdjustmentInput


class QuickQuoteFormalize(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    source_revision: int = Field(gt=0, le=2147483647)
    title: Name | None = None
    valid_until: date | None = None
    adjustments: list[QuoteAdjustmentInput] = Field(
        default_factory=list, max_length=100
    )
    final_price: NonNegativeMoney | None = None


class QuickQuoteFormalizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    quick_quote_id: UUID
    source_revision_id: UUID
    source_revision: int
    quote_id: UUID
    cost_calculation_id: UUID
    request_id: UUID
    created_at: datetime
