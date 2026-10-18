from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.costing.preview_schemas import PricingEvaluation, PricingPreviewCreate
from app.modules.products.schemas import Name


class QuickQuoteDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Name
    notes: str | None = Field(default=None, max_length=10000)
    pricing: PricingPreviewCreate


class QuickQuoteCreate(QuickQuoteDefinition):
    request_id: UUID


class QuickQuoteReplace(QuickQuoteCreate):
    expected_revision: int = Field(gt=0, le=2147483646)


class QuickQuoteRecalculate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    expected_revision: int = Field(gt=0, le=2147483646)


class QuickQuoteRead(BaseModel):
    id: UUID
    revision: int
    request_id: UUID
    operation: Literal["create", "replace", "recalculate"]
    definition: QuickQuoteDefinition
    evaluation: PricingEvaluation
    created_at: datetime
