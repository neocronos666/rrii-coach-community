from datetime import datetime
from decimal import Decimal
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.assets.schemas import Description, Name


class FamilyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name
    description: Description | None = None


class FamilyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name | None = None
    description: Description | None = None

    @model_validator(mode="after")
    def name_not_null(self) -> Self:
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name no admite null")
        return self


class FamilyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class ComponentInput(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    child_asset_id: UUID
    child_revision_id: UUID
    quantity: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=6)]


class CompositionRevisionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_revision_id: UUID
    components: list[ComponentInput]
    note: Description | None = None

    @model_validator(mode="after")
    def unique_children(self) -> Self:
        children = [item.child_asset_id for item in self.components]
        if len(children) != len(set(children)):
            raise ValueError("Un hijo aparece una sola vez; indicar su cantidad")
        return self


class ComponentRead(ComponentInput):
    id: UUID
    parent_revision_id: UUID


class ComponentUpdateRead(BaseModel):
    child_asset_id: UUID
    code: str
    name: str
    archived: bool
    pinned_revision_id: UUID
    pinned_revision_number: int
    current_revision_id: UUID
    current_revision_number: int
    update_available: bool


class RelatedAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    family_id: UUID | None
    archived: bool


class CompatibilityPage(BaseModel):
    items: list[RelatedAssetRead]
    total: int
    offset: int
    limit: int
