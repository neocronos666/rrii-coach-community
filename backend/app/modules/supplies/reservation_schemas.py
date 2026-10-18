from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.supplies.schemas import SupplyUnit


class ReservationSet(BaseModel):
    model_config = ConfigDict(extra="forbid")
    quantity: Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=6)]


class ReservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    task_id: UUID
    supply_id: UUID
    quantity: Decimal
    unit: SupplyUnit
    created_at: datetime
    updated_at: datetime


class SupplyAvailabilityRead(BaseModel):
    supply_id: UUID
    unit: SupplyUnit
    physical_quantity: Decimal
    reserved_quantity: Decimal
    available_quantity: Decimal
    shortage_warning: bool


class ReservationResult(BaseModel):
    reservation: ReservationRead
    availability: SupplyAvailabilityRead
