from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class StockMovementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    movement_type: Literal["purchase", "adjustment_in", "adjustment_out"]
    quantity: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=6)]
    reason: Annotated[str, Field(min_length=1, max_length=2000)]
    occurred_at: AwareDatetime | None = None


class StockMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    test_print_id: UUID | None
    variant_id: UUID
    quantity: Decimal
    unit: str
    movement_type: str
    allocation_id: UUID | None
    run_consumption_id: UUID | None
    run_id: UUID | None
    request_id: UUID | None
    reason: str | None
    occurred_at: datetime
    created_at: datetime


class ProductStockRead(BaseModel):
    variant_id: UUID
    unit: str
    physical_quantity: Decimal
    allocated_quantity: Decimal
    available_quantity: Decimal
    shortage_warning: bool
