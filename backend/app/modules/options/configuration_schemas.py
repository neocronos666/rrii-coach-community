from decimal import Decimal
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

Quantity = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=6)]
SelectionCount = Annotated[int, Field(ge=0, strict=True)]


class AllowedOptionValue(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    value_id: UUID
    default_quantity: Quantity | None = None


class ProductOptionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    definition_id: UUID
    min_selections: SelectionCount = 0
    max_selections: SelectionCount | None = 1
    context_asset_id: UUID | None = None
    context_definition_id: UUID | None = None
    values: list[AllowedOptionValue]

    @model_validator(mode="after")
    def valid_configuration(self) -> Self:
        if (
            self.max_selections is not None
            and self.max_selections < self.min_selections
        ):
            raise ValueError("max_selections debe ser mayor o igual a min_selections")
        ids = [value.value_id for value in self.values]
        if len(ids) != len(set(ids)):
            raise ValueError("Una opción permitida aparece una sola vez")
        if len(ids) < self.min_selections:
            raise ValueError("No hay suficientes opciones para el mínimo requerido")
        defaults = sum(value.default_quantity is not None for value in self.values)
        if defaults and (
            defaults < self.min_selections
            or (self.max_selections is not None and defaults > self.max_selections)
        ):
            raise ValueError("Los defaults deben formar una selección válida")
        if self.context_asset_id is not None and self.context_definition_id is not None:
            raise ValueError("Indicar un único origen de contexto")
        if self.context_definition_id == self.definition_id:
            raise ValueError("Una característica no puede ser su propio contexto")
        return self


class ProductConfigurationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    options: list[ProductOptionInput]

    @model_validator(mode="after")
    def unique_definitions(self) -> Self:
        ids = [option.definition_id for option in self.options]
        if len(ids) != len(set(ids)):
            raise ValueError("Una característica aparece una sola vez en el producto")
        return self


class ProductConfigurationRead(ProductConfigurationInput):
    product_id: UUID


class SelectedOptionValue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value_id: UUID
    quantity: Quantity = Decimal("1")


class OptionSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    definition_id: UUID
    values: list[SelectedOptionValue]

    @model_validator(mode="after")
    def unique_values(self) -> Self:
        ids = [value.value_id for value in self.values]
        if len(ids) != len(set(ids)):
            raise ValueError("Una opción aparece una vez; indicar su cantidad")
        return self


class ConfigurationResolveInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    selections: list[OptionSelection] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_definitions(self) -> Self:
        ids = [selection.definition_id for selection in self.selections]
        if len(ids) != len(set(ids)):
            raise ValueError("Una característica aparece una sola vez")
        return self


class ResolvedOptionValue(BaseModel):
    value_id: UUID
    quantity: Decimal
    family_id: UUID | None
    asset_id: UUID | None
    revision_id: UUID | None
    supply_id: UUID | None = None
    supply_unit: str | None = None


class ResolvedOptionSelection(BaseModel):
    definition_id: UUID
    context_asset_id: UUID | None
    values: list[ResolvedOptionValue]


class ResolvedConfiguration(BaseModel):
    product_id: UUID
    selections: list[ResolvedOptionSelection]
