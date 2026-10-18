from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.orders.types import OrderStatus


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    source_quote_id: UUID
    source_quote_item_id: UUID
    title: str
    description: str
    status: OrderStatus
    quantity: Decimal
    currency: str
    technical_unit_cost: Decimal
    technical_total_cost: Decimal
    quoted_suggested_price: Decimal
    quoted_final_price: Decimal
    notes: str | None
    created_at: datetime
    updated_at: datetime
