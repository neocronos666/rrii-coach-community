from datetime import datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StringConstraints,
    field_validator,
    model_validator,
)

Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
]
Description = Annotated[str, StringConstraints(max_length=10000)]


class CategoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    system_key: str | None
    created_at: datetime
    updated_at: datetime


class AssetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name
    description: Description | None = None
    category_id: UUID | None = None
    family_id: UUID | None = None
    third_party: bool = False
    author: Name | None = None
    origin: Name | None = None
    license: Name | None = None
    source_url: str | None = Field(default=None, max_length=2048)
    usage_notes: Description | None = None
    revision_note: Description | None = None

    @field_validator("source_url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        return str(HttpUrl(value)) if value is not None else None


class AssetUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name | None = None
    description: Description | None = None
    category_id: UUID | None = None
    family_id: UUID | None = None
    third_party: bool | None = None
    author: Name | None = None
    origin: Name | None = None
    license: Name | None = None
    source_url: str | None = Field(default=None, max_length=2048)
    usage_notes: Description | None = None
    archived: bool | None = None

    @field_validator("source_url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        return str(HttpUrl(value)) if value is not None else None

    @model_validator(mode="after")
    def required_not_null(self) -> Self:
        for field in ("name", "category_id", "third_party", "archived"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} no admite null")
        return self


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    description: str | None
    category_id: UUID
    family_id: UUID | None
    current_revision_id: UUID
    archived: bool
    third_party: bool
    author: str | None
    origin: str | None
    license: str | None
    source_url: str | None
    usage_notes: str | None
    created_at: datetime
    updated_at: datetime


class RevisionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note: Description | None = None


class RevisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    asset_id: UUID
    number: int
    note: str | None
    restored_from_revision_id: UUID | None
    created_at: datetime
