from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin


class FileRole(StrEnum):
    MANUFACTURING = "manufacturing"
    SOURCE = "source"
    DOCUMENTATION = "documentation"
    REFERENCE = "reference"
    MEDIA = "media"
    THUMBNAIL = "thumbnail"


class StoredFile(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "stored_files"
    __table_args__ = (
        CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="sha256_format"),
        CheckConstraint("size_bytes > 0", name="size_positive"),
    )
    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    detected_mime: Mapped[str] = mapped_column(String(127))
    storage_key: Mapped[str] = mapped_column(String(80), unique=True)
    technical_metadata: Mapped[dict[str, str | int]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AssetRevisionFile(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "asset_revision_files"
    __table_args__ = (
        UniqueConstraint(
            "revision_id", "filename", name="uq_asset_revision_files_name"
        ),
        Index(
            "uq_asset_revision_files_thumbnail",
            "revision_id",
            unique=True,
            postgresql_where=text("role = 'thumbnail'"),
        ),
        CheckConstraint(
            "role IN ('manufacturing', 'source', 'documentation', "
            "'reference', 'media', 'thumbnail')",
            name="role_valid",
        ),
        CheckConstraint("length(trim(filename)) > 0", name="filename_nonempty"),
    )
    revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("asset_revisions.id", ondelete="RESTRICT"), index=True
    )
    stored_file_id: Mapped[UUID] = mapped_column(
        ForeignKey("stored_files.id", ondelete="RESTRICT"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32))
    attached_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )
