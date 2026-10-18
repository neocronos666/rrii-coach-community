from datetime import datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.modules.supplies.schemas import SupplyUnit

Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
]
Sku = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, to_upper=True, min_length=1, max_length=100
    ),
]
AttributeKey = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
AttributeValue = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
]


class VariantCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name
    sku: Sku | None = None
    description: str | None = None
    base_unit: SupplyUnit
    attributes: dict[AttributeKey, AttributeValue] = Field(
        default_factory=dict, max_length=30
    )
    active: bool = True

    @field_validator("sku", mode="before")
    @classmethod
    def normalize_sku(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value


class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name
    description: str | None = None
    active: bool = True
    initial_variant: VariantCreate


class ProductUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name | None = None
    description: str | None = None
    active: bool | None = None

    @model_validator(mode="after")
    def required_not_null(self) -> Self:
        for field in ("name", "active", "attributes"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} no admite null")
        return self


class VariantUpdate(ProductUpdate):
    sku: Sku | None = None
    attributes: dict[AttributeKey, AttributeValue] | None = Field(
        default=None, max_length=30
    )

    @field_validator("sku", mode="before")
    @classmethod
    def normalize_sku(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str | None
    active: bool
    created_at: datetime
    updated_at: datetime


class VariantRead(ProductRead):
    product_id: UUID
    sku: str | None
    base_unit: SupplyUnit
    attributes: dict[str, str]


class ProductCreated(ProductRead):
    initial_variant: VariantRead
