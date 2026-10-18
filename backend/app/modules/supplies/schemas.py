from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.validation import CurrencyCode, NonNegativeMoney

PositiveQuantity = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=6)]


class SupplyCategory(StrEnum):
    MATERIAL = "material"
    COMPONENT = "component"
    CONSUMABLE = "consumable"
    PACKAGING = "packaging"
    SPARE_PART = "spare_part"
    MERCHANDISE = "merchandise"
    OTHER = "other"


class SupplyUnit(StrEnum):
    UNIT = "unit"
    GRAM = "g"
    KILOGRAM = "kg"
    MILLILITER = "ml"
    LITER = "l"
    MILLIMETER = "mm"
    CENTIMETER = "cm"
    METER = "m"
    SQUARE_METER = "m2"
    CUBIC_METER = "m3"


class SupplyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    sku: str | None = Field(default=None, min_length=1, max_length=100)
    category: SupplyCategory
    brand: str | None = Field(default=None, max_length=255)
    base_unit: SupplyUnit
    description: str | None = None
    active: bool = True
    notes: str | None = None


class SupplyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    sku: str | None = Field(default=None, min_length=1, max_length=100)
    category: SupplyCategory | None = None
    brand: str | None = Field(default=None, max_length=255)
    base_unit: SupplyUnit | None = None
    description: str | None = None
    active: bool | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def reject_null_for_required_fields(self) -> Self:
        for field_name in ("name", "category", "base_unit", "active"):
            if (
                field_name in self.model_fields_set
                and getattr(self, field_name) is None
            ):
                raise ValueError(f"{field_name} no admite null")
        return self


class SupplyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    sku: str | None
    category: SupplyCategory
    brand: str | None
    base_unit: SupplyUnit
    description: str | None
    active: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime


class PresentationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    quantity: PositiveQuantity
    unit: SupplyUnit
    purchase_price: NonNegativeMoney | None = None
    currency: CurrencyCode | None = None
    active: bool = True

    @model_validator(mode="after")
    def validate_price_currency_pair(self) -> Self:
        if (self.purchase_price is None) != (self.currency is None):
            raise ValueError("purchase_price y currency deben informarse juntos")
        return self


class PresentationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    supply_id: UUID
    name: str
    quantity: Decimal
    unit: SupplyUnit
    purchase_price: Decimal | None
    currency: CurrencyCode | None
    active: bool
    created_at: datetime
    updated_at: datetime


class PurchaseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantity: PositiveQuantity
    presentation_id: UUID | None = None
    total_cost: NonNegativeMoney
    currency: CurrencyCode
    purchased_at: datetime
    notes: str | None = None


class PurchaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    supply_id: UUID
    presentation_id: UUID | None
    quantity: Decimal
    total_cost: Decimal
    currency: CurrencyCode
    purchased_at: datetime
    notes: str | None
    created_at: datetime
    updated_at: datetime


class AdjustmentDirection(StrEnum):
    IN = "in"
    OUT = "out"


class AdjustmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    direction: AdjustmentDirection
    quantity: PositiveQuantity
    reason: str = Field(min_length=1, max_length=2000)
    occurred_at: datetime


class MovementType(StrEnum):
    CONSUMPTION = "consumption"
    PURCHASE = "purchase"
    ADJUSTMENT_IN = "adjustment_in"
    ADJUSTMENT_OUT = "adjustment_out"


class MovementRead(BaseModel):
    purchase_id: UUID | None
    model_config = ConfigDict(from_attributes=True)

    run_consumption_id: UUID | None

    id: UUID
    supply_id: UUID
    movement_type: MovementType
    quantity: Decimal
    occurred_at: datetime
    notes: str | None
    created_at: datetime


class StockRead(BaseModel):
    supply_id: UUID
    quantity: Decimal
    unit: SupplyUnit


class EstimatedCostRead(BaseModel):
    supply_id: UUID
    unit: SupplyUnit
    currency: CurrencyCode
    unit_cost: Decimal
    source: str = "last_purchase"
