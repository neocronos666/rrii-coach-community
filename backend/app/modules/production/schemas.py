from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.production.types import (
    ProductionTaskPriority,
    ProductionTaskStatus,
    ProductionTaskType,
)

PositiveQuantity = Annotated[
    Decimal,
    Field(gt=0, max_digits=18, decimal_places=6),
]


class ProductionTaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output_variant_id: UUID | None = None
    task_type: ProductionTaskType
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    priority: ProductionTaskPriority = ProductionTaskPriority.NORMAL
    planned_quantity: PositiveQuantity
    planned_unit: str | None = Field(default=None, max_length=30)
    machine_id: UUID | None = None
    queue_position: int = Field(default=1000, ge=0)
    production_parameters: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None


class ProductionTaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    priority: ProductionTaskPriority | None = None
    planned_quantity: PositiveQuantity | None = None
    machine_id: UUID | None = None
    queue_position: int | None = Field(default=None, ge=0)
    production_parameters: dict[str, Any] | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def reject_null_for_non_nullable_fields(self) -> Self:
        for field_name in (
            "title",
            "priority",
            "planned_quantity",
            "queue_position",
            "production_parameters",
        ):
            if (
                field_name in self.model_fields_set
                and getattr(self, field_name) is None
            ):
                raise ValueError(f"{field_name} no admite null")
        return self


class ProductionTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    production_plan_id: UUID | None
    recipe_step_key: str | None
    recipe_snapshot: dict[str, Any] | None
    execution_mode: str
    origin: str
    output_variant_id: UUID | None
    recipe_id: UUID | None
    order_id: UUID | None
    project_component_id: UUID | None
    task_type: ProductionTaskType
    title: str
    description: str | None
    status: ProductionTaskStatus
    priority: ProductionTaskPriority
    planned_quantity: Decimal
    planned_unit: str | None
    machine_id: UUID | None
    queue_position: int
    production_parameters: dict[str, Any]
    notes: str | None
    started_at: datetime | None
    paused_at: datetime | None
    physically_completed_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ProductionTaskDependencyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    depends_on_task_id: UUID


class ProductionTaskDependencyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: UUID
    depends_on_task_id: UUID
    created_at: datetime
    prerequisite: ProductionTaskRead
