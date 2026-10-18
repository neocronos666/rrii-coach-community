from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.modules.products.consumption_schemas import RunProductConsumptionCreate
from app.modules.supplies.consumption_schemas import RunSupplyConsumptionCreate

NonNegativeQuantity = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=6)]


class FailureReason(StrEnum):
    POWER_FAILURE = "power_failure"
    MACHINE_FAILURE = "machine_failure"
    ADHESION = "adhesion"
    WARPING = "warping"
    LAYER_SHIFT = "layer_shift"
    MATERIAL_FAILURE = "material_failure"
    OPERATOR_ERROR = "operator_error"
    QUALITY_FAILURE = "quality_failure"
    OTHER = "other"


class RunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    machine_id: UUID | None = None
    started_at: AwareDatetime | None = None
    parameters: dict[str, Any] | None = None


class RunClose(BaseModel):
    model_config = ConfigDict(extra="forbid")
    supply_consumptions: list[RunSupplyConsumptionCreate] = Field(
        default_factory=list, max_length=100
    )
    product_consumptions: list[RunProductConsumptionCreate] = Field(
        default_factory=list, max_length=100
    )
    good_quantity: NonNegativeQuantity
    failed_quantity: NonNegativeQuantity = Decimal("0")
    failure_reason: FailureReason | None = None
    ended_at: AwareDatetime | None = None
    actual_duration_seconds: NonNegativeQuantity | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def unique_supplies(self) -> Self:
        if len({item.variant_id for item in self.product_consumptions}) != len(
            self.product_consumptions
        ):
            raise ValueError("Cada variante se registra una sola vez por Run")
        if len({item.supply_id for item in self.supply_consumptions}) != len(
            self.supply_consumptions
        ):
            raise ValueError("Cada insumo se registra una sola vez por Run")
        return self


class RunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    task_id: UUID | None
    test_print_step_id: UUID | None
    request_id: UUID
    machine_id: UUID | None
    output_variant_id: UUID | None
    unit: str | None
    status: str
    warnings: list[str]
    parameters: dict[str, Any]
    started_at: datetime
    ended_at: datetime | None
    good_quantity: Decimal | None
    failed_quantity: Decimal | None
    actual_duration_seconds: Decimal | None
    failure_reason: FailureReason | None
    notes: str | None


class TaskProgressRead(BaseModel):
    task_id: UUID
    target_quantity: Decimal
    good_quantity: Decimal
    failed_quantity: Decimal
    remaining_quantity: Decimal
    excess_quantity: Decimal
    closed_runs: int
