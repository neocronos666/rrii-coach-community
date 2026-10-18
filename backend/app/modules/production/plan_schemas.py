from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.options.configuration_schemas import (
    ConfigurationResolveInput,
    ResolvedConfiguration,
)
from app.modules.production.schemas import PositiveQuantity, ProductionTaskRead
from app.modules.recipes.schemas import PlannedStep, StepKey


class PlanPreviewCreate(ConfigurationResolveInput):
    model_config = ConfigDict(extra="forbid")
    target_quantity: PositiveQuantity
    variant_id: UUID | None = None


class ProductionPlanCreate(PlanPreviewCreate):
    request_id: UUID
    recipe_id: UUID
    reserve_supplies: bool = True
    allocate_output: bool = True
    machine_assignments: dict[StepKey, UUID] = Field(
        default_factory=dict, max_length=100
    )


class ProductionPreview(BaseModel):
    configuration: ResolvedConfiguration | None = None
    omitted_step_keys: list[str] = Field(default_factory=list)
    recipe_id: UUID
    target_quantity: Decimal
    steps: list[PlannedStep]


class ProductionPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    recipe_id: UUID
    variant_id: UUID
    order_id: UUID | None
    project_component_id: UUID | None
    allocation_id: UUID | None
    target_quantity: Decimal
    request_id: UUID
    snapshot: dict[str, Any]
    created_at: datetime
    tasks: list[ProductionTaskRead]
    warnings: list[str]
