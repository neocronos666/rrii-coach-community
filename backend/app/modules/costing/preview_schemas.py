from decimal import Decimal
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.validation import NonNegativeMoney
from app.modules.costing.schemas import (
    LaborCostInput,
    ManualExtraInput,
    NonNegativeQuantity,
)
from app.modules.options.configuration_schemas import (
    ConfigurationResolveInput,
    ResolvedConfiguration,
)
from app.modules.recipes.schemas import PlannedStep, PlanRead, StepKey
from app.modules.supplies.schemas import PositiveQuantity


class StepCostEstimate(BaseModel):
    """Importes y tiempos totales del paso para la demanda solicitada, no por lote."""

    model_config = ConfigDict(extra="forbid")
    machine_id: UUID | None = None
    machine_duration_minutes: int | None = Field(default=None, gt=0)
    energy_kwh: NonNegativeQuantity | None = None
    labor: list[LaborCostInput] = Field(default_factory=list, max_length=100)
    extras: list[ManualExtraInput] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def paired_machine(self) -> Self:
        if (self.machine_id is None) != (self.machine_duration_minutes is None):
            raise ValueError("Indicar máquina y duración juntas")
        return self


class PricingPreviewCreate(ConfigurationResolveInput):
    recipe_id: UUID
    variant_id: UUID
    target_quantity: PositiveQuantity
    strategy: Literal["fifo", "last_purchase"] = "fifo"
    step_estimates: dict[StepKey, StepCostEstimate] = Field(
        default_factory=dict, max_length=100
    )
    markup_percentage: NonNegativeMoney | None = None


class PreviewLine(BaseModel):
    step_key: str
    category: str
    description: str
    quantity: Decimal
    unit: str
    unit_cost: Decimal | None
    subtotal: Decimal | None
    currency: str | None
    source: str
    source_reference: str | None = None
    supply_id: UUID | None = None
    movement_id: UUID | None = None
    purchase_id: UUID | None = None
    complete: bool


class PricingPreviewRead(BaseModel):
    recipe_id: UUID
    variant_id: UUID
    target_quantity: Decimal
    strategy: Literal["fifo", "last_purchase"]
    planned_steps: list[PlannedStep]
    omitted_step_keys: list[str]
    lines: list[PreviewLine]
    totals_by_currency: dict[str, Decimal]
    complete: bool
    multi_currency: bool
    warnings: list[str]
    markup_percentage: Decimal | None
    suggested_price: Decimal | None
    suggested_currency: str | None


class PricingEvaluation(BaseModel):
    """Contexto efectivo y resultado del mismo snapshot de lectura."""

    preview: PricingPreviewRead
    plan: PlanRead
    configuration: ResolvedConfiguration | None
    product_id: UUID
    product_name: str
    variant_name: str
    variant_unit: str
    recipe_name: str
