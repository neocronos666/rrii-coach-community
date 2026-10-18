from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from app.modules.assets.file_models import FileRole


def validate_filename(value: str) -> str:
    if (
        not value.strip()
        or value in {".", ".."}
        or any(ord(char) < 32 or ord(char) == 127 or char in "/\\" for char in value)
    ):
        raise ValueError("El nombre debe ser un archivo sin rutas ni controles")
    return value


Filename = Annotated[
    str, Field(min_length=1, max_length=255), BeforeValidator(validate_filename)
]


class RevisionFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    revision_id: UUID
    stored_file_id: UUID
    filename: str
    role: FileRole
    attached_at: datetime
    sha256: str
    size_bytes: int
    detected_mime: str
    technical_metadata: dict[str, str | int]


class FileDifference(BaseModel):
    filename: str
    before: RevisionFileRead | None
    after: RevisionFileRead | None


class RevisionFilesDiff(BaseModel):
    from_revision_id: UUID
    to_revision_id: UUID
    added: list[FileDifference]
    removed: list[FileDifference]
    content_changed: list[FileDifference]
    role_changed: list[FileDifference]
    unchanged: list[str]


class FileErrorRead(BaseModel):
    detail: str | list[dict[str, object]]
