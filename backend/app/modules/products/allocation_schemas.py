from datetime import datetime
from decimal import Decimal
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.products.stock_schemas import ProductStockRead

Quantity = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=6)]


class AllocationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    variant_id: UUID
    order_id: UUID | None = None
    project_component_id: UUID | None = None
    quantity: Quantity

    @model_validator(mode="after")
    def destination(self) -> Self:
        if (self.order_id is None) == (self.project_component_id is None):
            raise ValueError("Indicar Order o ProjectComponent, exclusivamente")
        return self


class AllocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    variant_id: UUID
    order_id: UUID | None
    project_component_id: UUID | None
    quantity: Decimal
    initial_quantity: Decimal
    unit: str
    request_id: UUID
    created_at: datetime
    updated_at: datetime


class AllocationDelivery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    quantity: Quantity


class AllocationResult(BaseModel):
    allocation: AllocationRead
    stock: ProductStockRead
