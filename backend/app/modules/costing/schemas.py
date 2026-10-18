from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.validation import CurrencyCode, NonNegativeMoney
from app.modules.supplies.schemas import PositiveQuantity, SupplyUnit

NonNegativeQuantity = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=6)]


class CostCategory(StrEnum):
    MATERIAL = "material"
    COMPONENT = "component"
    CONSUMABLE = "consumable"
    PACKAGING = "packaging"
    MACHINE_TIME = "machine_time"
    ENERGY = "energy"
    DESIGN_LABOR = "design_labor"
    PREPRODUCTION_LABOR = "preproduction_labor"
    POSTPRODUCTION_LABOR = "postproduction_labor"
    ASSEMBLY_LABOR = "assembly_labor"
    SUPPORT_LABOR = "support_labor"
    TRAINING_LABOR = "training_labor"
    PRETRANSPORT = "pretransport"
    EXTRA = "extra"


class LaborType(StrEnum):
    DESIGN = "design"
    PREPRODUCTION = "preproduction"
    POSTPRODUCTION = "postproduction"
    ASSEMBLY = "assembly"
    SUPPORT = "support"
    TRAINING = "training"
    PRETRANSPORT = "pretransport"


class SupplyCostInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    supply_id: UUID
    quantity: PositiveQuantity
    unit: SupplyUnit


class LaborCostInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    labor_type: LaborType
    duration_minutes: int = Field(gt=0)


class ManualExtraInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str = Field(min_length=1, max_length=1000)
    amount: NonNegativeMoney
    currency: CurrencyCode


class CostCalculationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    machine_id: UUID | None = None
    machine_duration_minutes: int | None = Field(default=None, gt=0)
    energy_kwh: NonNegativeQuantity | None = None
    supplies: list[SupplyCostInput] = Field(default_factory=list)
    labor: list[LaborCostInput] = Field(default_factory=list)
    extras: list[ManualExtraInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_machine_duration(self) -> Self:
        if self.machine_duration_minutes is not None and self.machine_id is None:
            raise ValueError("machine_duration_minutes requiere machine_id")
        if not (
            self.supplies
            or self.labor
            or self.extras
            or self.energy_kwh is not None
            or self.machine_duration_minutes is not None
        ):
            raise ValueError("El cálculo requiere al menos un componente de costo")
        return self


class CostLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    category: CostCategory
    description: str
    quantity: Decimal
    unit: str
    unit_cost: Decimal | None
    currency: CurrencyCode | None
    subtotal: Decimal | None
    source: str
    source_reference: str | None
    complete: bool
    created_at: datetime


class CostCalculationRead(BaseModel):
    demand_quantity: Decimal | None = None
    demand_unit: str | None = None
    id: UUID
    calculation_type: str
    complete: bool
    multi_currency: bool
    lines: list[CostLineRead]
    totals_by_currency: dict[str, Decimal]
    warnings: list[str]
    calculated_at: datetime
    created_at: datetime
