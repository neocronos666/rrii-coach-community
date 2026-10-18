from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.modules.machines.schemas import MachineType
from app.modules.production.types import ProductionTaskType
from app.modules.products.schemas import Name
from app.modules.recipes.action_templates import template_parts
from app.modules.recipes.service_schemas import ActionTemplate, ContextText, Placeholder
from app.modules.recipes.types import RecipeStepKind
from app.modules.supplies.schemas import PositiveQuantity, SupplyUnit

StepKey = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,79}$")]


class RecipeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name
    description: str | None = None
    active: bool = True


class SupplyInputCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    supply_id: UUID
    quantity_per_batch: PositiveQuantity


class SelectedSupplyInput(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    definition_id: UUID
    quantity_per_batch: PositiveQuantity
    unit: SupplyUnit


class ProductInputCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_variant_id: UUID
    quantity_per_batch: PositiveQuantity
    source_step_key: StepKey | None = None


class ResourceInput(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    key: StepKey
    asset_revision_id: UUID
    quantity_per_batch: PositiveQuantity = Decimal("1")
    label: Name | None = None


class ResourceRead(ResourceInput):
    asset_id: UUID
    code: str
    name: str
    revision_number: int
    archived: bool


class SelectionCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    definition_id: UUID
    value_id: UUID


class SelectionResourceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: StepKey
    from_selection: SelectionCondition
    quantity_per_batch: PositiveQuantity = Decimal("1")
    label: Name | None = None


class StepCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: StepKey
    title: Name
    when_selected: SelectionCondition | None = None
    scale_by_selection: bool = False
    task_type: ProductionTaskType = ProductionTaskType.MANUAL
    kind: RecipeStepKind = RecipeStepKind.OPERATION
    service_definition_id: UUID | None = None
    action_template: ActionTemplate | None = None
    action_context: dict[Placeholder, ContextText] = Field(
        default_factory=dict,
        description=(
            "Etiquetas explícitas con precedencia. En recetas base, la resolución "
            "completa placeholders ausentes desde producto, demanda del paso y "
            "recurso único; el plan resuelto incluye el contexto efectivo."
        ),
    )
    unit: SupplyUnit = SupplyUnit.UNIT
    quantity_per_output: PositiveQuantity = Decimal("1")
    batch_yield: PositiveQuantity = Decimal("1")
    is_final_output: bool = False
    output_variant_id: UUID | None = None
    required_machine_type: MachineType | None = None
    instructions: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    supply_inputs: list[SupplyInputCreate] = Field(default_factory=list, max_length=100)
    selected_supply_inputs: list[SelectedSupplyInput] = Field(
        default_factory=list, max_length=100
    )
    product_inputs: list[ProductInputCreate] = Field(
        default_factory=list, max_length=100
    )
    resources: Sequence[ResourceInput | SelectionResourceInput] = Field(
        default_factory=list, max_length=100
    )
    depends_on: list[StepKey] = Field(default_factory=list, max_length=100)

    @model_validator(mode="before")
    @classmethod
    def infer_legacy_print(cls, value: Any) -> Any:
        if isinstance(value, dict) and "kind" not in value:
            if value.get("task_type") in {"fdm_print", "sla_print"}:
                return {**value, "kind": RecipeStepKind.PRINT}
        return value

    @field_validator("action_template")
    @classmethod
    def valid_template(cls, value: str | None) -> str | None:
        if value is not None:
            template_parts(value)
        return value

    @model_validator(mode="after")
    def validate_kind(self) -> Self:
        if len(self.supply_inputs) + len(self.selected_supply_inputs) > 100:
            raise ValueError("El paso admite como máximo 100 insumos en total")
        if len({item.definition_id for item in self.selected_supply_inputs}) != len(
            self.selected_supply_inputs
        ):
            raise ValueError("La característica de material no se repite en un paso")
        if self.scale_by_selection and (
            self.when_selected is None or self.is_final_output
        ):
            raise ValueError(
                "Escalar requiere una selección y no admite la salida final"
            )
        if len({resource.key for resource in self.resources}) != len(self.resources):
            raise ValueError("La clave de recurso debe ser única dentro del paso")
        if (self.kind == RecipeStepKind.SERVICE) != (
            self.service_definition_id is not None
        ):
            raise ValueError(
                "Un paso service debe referenciar un servicio; los demás no"
            )
        if self.kind != RecipeStepKind.SERVICE and (
            self.action_template is not None or self.action_context
        ):
            raise ValueError("La frase contextual pertenece a un paso service")
        printing = self.task_type in {
            ProductionTaskType.FDM_PRINT,
            ProductionTaskType.SLA_PRINT,
        }
        if (self.kind == RecipeStepKind.PRINT) != printing:
            raise ValueError("El tipo print requiere una tecnología de impresión")
        if self.kind == RecipeStepKind.SERVICE and self.task_type not in {
            ProductionTaskType.MANUAL,
            ProductionTaskType.ASSEMBLY,
            ProductionTaskType.POSTPROCESSING,
        }:
            raise ValueError("El servicio humano requiere una tarea manual")
        if self.kind in {RecipeStepKind.SERVICE, RecipeStepKind.WAIT} and (
            self.required_machine_type is not None
        ):
            raise ValueError("Service y wait no asignan máquina")
        if self.kind == RecipeStepKind.WAIT and (
            self.task_type != ProductionTaskType.MANUAL
            or self.output_variant_id is not None
            or self.is_final_output
            or self.supply_inputs
            or self.selected_supply_inputs
            or self.product_inputs
            or self.parameters
        ):
            raise ValueError("Wait es una instrucción textual sin salida ni consumos")
        return self


class RecipePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    steps: list[StepCreate] = Field(max_length=100)

    @model_validator(mode="after")
    def validate_dag(self) -> Self:
        graph = {step.key: step.depends_on for step in self.steps}
        if len(graph) != len(self.steps):
            raise ValueError("Las claves de paso deben ser únicas")
        resolved: set[str] = set()
        pending = set(graph)
        for step in self.steps:
            if len(set(step.depends_on)) != len(step.depends_on):
                raise ValueError("Dependencia duplicada")
            if any(key not in graph for key in step.depends_on):
                raise ValueError("La dependencia debe pertenecer a esta receta")
        while pending:
            ready = {key for key in pending if set(graph[key]) <= resolved}
            if not ready:
                raise ValueError("Las dependencias deben formar un DAG")
            resolved.update(ready)
            pending.difference_update(ready)
        by_key = {step.key: step for step in self.steps}
        for step in self.steps:
            if len({item.supply_id for item in step.supply_inputs}) != len(
                step.supply_inputs
            ):
                raise ValueError("Insumo duplicado en un paso")
            if len({item.product_variant_id for item in step.product_inputs}) != len(
                step.product_inputs
            ):
                raise ValueError("Variante duplicada en un paso")
            for item in step.product_inputs:
                if item.source_step_key is not None:
                    source = by_key.get(item.source_step_key)
                    if source is None or source.key not in step.depends_on:
                        raise ValueError(
                            "El paso proveedor debe ser un prerrequisito directo"
                        )
                    if source.output_variant_id != item.product_variant_id:
                        raise ValueError(
                            "El paso proveedor no produce la variante requerida"
                        )
        return self


class RecipeRead(RecipeCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    product_id: UUID
    product_variant_id: UUID | None
    created_at: datetime
    updated_at: datetime


class StepRead(StepCreate):
    resources: list[ResourceRead | SelectionResourceInput] = Field(
        default_factory=list, max_length=100
    )
    id: UUID
    position: int
    service_name: str | None = None
    service_action: str | None = Field(
        default=None,
        description=(
            "Frase resuelta; null si no es un servicio o la receta base requiere "
            "resolver configuración/cantidad. En resolución de un servicio es texto."
        ),
    )
    service_instructions: str | None = None


class PlanRead(BaseModel):
    recipe_id: UUID
    steps: list[StepRead]


class PlannedStep(BaseModel):
    key: str
    required_quantity: Decimal
    batches: Decimal
    planned_capacity: Decimal
    unit: SupplyUnit
