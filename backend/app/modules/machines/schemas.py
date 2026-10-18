from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.validation import CurrencyCode, NonNegativeMoney

NonNegativeMeasurement = Annotated[
    Decimal,
    Field(ge=0, max_digits=12, decimal_places=2),
]


class MachineType(StrEnum):
    FDM_PRINTER = "fdm_printer"
    SLA_PRINTER = "sla_printer"
    CNC = "cnc"
    LASER = "laser"
    SCANNER = "scanner"
    WASHER = "washer"
    CURING_STATION = "curing_station"
    PAPER_PRINTER = "paper_printer"
    LABEL_PRINTER = "label_printer"
    PLOTTER = "plotter"
    VINYL_CUTTER = "vinyl_cutter"
    HEAT_PRESS = "heat_press"
    ENGRAVER = "engraver"
    OTHER = "other"


class MachineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    machine_type: MachineType
    manufacturer: str | None = Field(default=None, max_length=255)
    model: str | None = Field(default=None, max_length=255)
    purchase_date: date | None = None
    purchase_price: NonNegativeMoney | None = None
    currency: CurrencyCode | None = None
    rated_power_w: NonNegativeMeasurement | None = None
    useful_life_hours: NonNegativeMeasurement | None = None
    active: bool = True
    notes: str | None = None


class MachineUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    machine_type: MachineType | None = None
    manufacturer: str | None = Field(default=None, max_length=255)
    model: str | None = Field(default=None, max_length=255)
    purchase_date: date | None = None
    purchase_price: NonNegativeMoney | None = None
    currency: CurrencyCode | None = None
    rated_power_w: NonNegativeMeasurement | None = None
    useful_life_hours: NonNegativeMeasurement | None = None
    active: bool | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def reject_null_for_required_fields(self) -> Self:
        for field_name in ("name", "machine_type", "currency", "active"):
            is_explicit_null = (
                field_name in self.model_fields_set
                and getattr(self, field_name) is None
            )
            if is_explicit_null:
                raise ValueError(f"{field_name} no admite null")
        return self


class MachineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    machine_type: MachineType
    manufacturer: str | None
    model: str | None
    purchase_date: date | None
    purchase_price: Decimal | None
    currency: CurrencyCode
    rated_power_w: Decimal | None
    useful_life_hours: Decimal | None
    active: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime
