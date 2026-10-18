from datetime import datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
]
Description = Annotated[str, StringConstraints(max_length=10000)]


class OptionDefinitionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name
    description: Description | None = None
    active: bool = True


class OptionDefinitionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name | None = None
    description: Description | None = None
    active: bool | None = None

    @model_validator(mode="after")
    def required_not_null(self) -> Self:
        for field in ("name", "active"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} no admite null")
        return self


class OptionDefinitionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str | None
    active: bool
    created_at: datetime
    updated_at: datetime


class OptionValueCreate(OptionDefinitionCreate):
    family_id: UUID | None = None
    supply_id: UUID | None = None


class OptionValueUpdate(OptionDefinitionUpdate):
    family_id: UUID | None = None
    supply_id: UUID | None = None


class OptionValueRead(OptionDefinitionRead):
    definition_id: UUID
    family_id: UUID | None
    supply_id: UUID | None


class OptionErrorRead(BaseModel):
    detail: str
