from datetime import datetime
from decimal import Decimal
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RunProductConsumptionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    variant_id: UUID
    consumed: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=6)]
    wasted: Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=6)] = Decimal(
        0
    )

    @model_validator(mode="after")
    def waste_subset(self) -> Self:
        if self.wasted > self.consumed:
            raise ValueError("El desperdicio es una parte del consumo")
        return self


class RunProductConsumptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    run_id: UUID
    variant_id: UUID
    consumed: Decimal
    wasted: Decimal
    unit: str
    created_at: datetime
    internal_source_step_id: UUID | None
