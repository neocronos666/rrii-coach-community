from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.projects.types import ProjectStatus


class ProjectComponentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_quote_item_id: UUID
    description: str
    quantity: Decimal
    technical_unit_cost: Decimal
    technical_total_cost: Decimal
    position: int
    notes: str | None
    created_at: datetime


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    source_quote_id: UUID
    title: str
    description: str | None
    status: ProjectStatus
    currency: str
    quoted_technical_cost: Decimal
    quoted_suggested_price: Decimal
    quoted_final_price: Decimal
    notes: str | None
    components: list[ProjectComponentRead]
    created_at: datetime
    updated_at: datetime
