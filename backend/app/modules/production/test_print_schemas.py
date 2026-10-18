from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.options.configuration_schemas import ConfigurationResolveInput
from app.modules.production.schemas import PositiveQuantity
from app.modules.recipes.schemas import StepKey


class TestPrintCreate(ConfigurationResolveInput):
    request_id: UUID
    recipe_id: UUID
    variant_id: UUID
    target_quantity: PositiveQuantity
    machine_assignments: dict[StepKey, UUID] = Field(
        default_factory=dict, max_length=100
    )


class TestPrintPromotion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    quantity: PositiveQuantity


class TestPrintStepRead(BaseModel):
    id: UUID
    key: str
    planned_quantity: Decimal
    good_quantity: Decimal
    failed_quantity: Decimal
    completed: bool
    open_run_id: UUID | None
    snapshot: dict[str, Any]


class TestPrintRead(BaseModel):
    id: UUID
    recipe_id: UUID
    variant_id: UUID
    target_quantity: Decimal
    unit: str
    status: str
    request_id: UUID
    snapshot: dict[str, Any]
    steps: list[TestPrintStepRead]
    promotion_movement_id: UUID | None
    promotable_quantity: Decimal
    created_at: datetime
