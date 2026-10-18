from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.modules.products.schemas import Name
from app.modules.recipes.action_templates import template_parts

InstructionText = Annotated[str, StringConstraints(max_length=10000)]
ActionTemplate = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)
]
ContextText = Annotated[str, StringConstraints(min_length=1, max_length=1000)]
Placeholder = Literal["piece", "design", "product", "quantity"]


class ServiceDefinitionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name
    instructions: InstructionText | None = None
    action_template: ActionTemplate | None = None
    active: bool = True

    @field_validator("action_template")
    @classmethod
    def validate_template(cls, value: str | None) -> str | None:
        if value is not None:
            template_parts(value)
        return value


class ServiceDefinitionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name | None = None
    instructions: InstructionText | None = None
    action_template: ActionTemplate | None = None
    active: bool | None = None

    @field_validator("action_template")
    @classmethod
    def validate_template(cls, value: str | None) -> str | None:
        if value is not None:
            template_parts(value)
        return value

    @model_validator(mode="after")
    def required_not_null(self) -> Self:
        for field in ("name", "active"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} no admite null")
        return self


class ServiceDefinitionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    instructions: str | None
    action_template: str | None
    active: bool
    created_at: datetime
    updated_at: datetime


class ServiceActionPreviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    values: dict[Placeholder, ContextText] = Field(default_factory=dict)


class ServiceActionPreview(BaseModel):
    service_definition_id: UUID
    action: str
    instructions: str | None


class ServiceDefinitionErrorRead(BaseModel):
    detail: str
