from datetime import datetime
from decimal import Decimal
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.supplies.schemas import PositiveQuantity, SupplyUnit


class RunSupplyConsumptionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    supply_id: UUID
    consumed: PositiveQuantity
    wasted: Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=6)] = Decimal(
        0
    )

    @model_validator(mode="after")
    def wasted_is_subset(self) -> Self:
        if self.wasted > self.consumed:
            raise ValueError("wasted debe ser una parte de consumed")
        return self


class RunSupplyConsumptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    run_id: UUID
    supply_id: UUID
    consumed: Decimal
    wasted: Decimal
    unit: SupplyUnit
    created_at: datetime
