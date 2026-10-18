from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Sequence,
    String,
    Text,
    UniqueConstraint,
    false,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

UNCATEGORIZED_ID = UUID("124db5f7-f482-4ca2-91d4-7f35cadf36f6")
asset_code_sequence = Sequence("asset_code_seq", metadata=Base.metadata)


class AssetCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "asset_categories"
    __table_args__ = (CheckConstraint("length(trim(name)) > 0", name="name_nonempty"),)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    system_key: Mapped[str | None] = mapped_column(String(40), unique=True)


class Asset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="name_nonempty"),
        ForeignKeyConstraint(
            ["id", "current_revision_id"],
            ["asset_revisions.asset_id", "asset_revisions.id"],
            name="fk_assets_current_revision",
            use_alter=True,
            ondelete="RESTRICT",
        ),
    )
    code: Mapped[str] = mapped_column(
        String(40),
        unique=True,
        server_default=text("'AST-' || nextval('asset_code_seq')::text"),
    )
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("asset_categories.id", ondelete="RESTRICT"), index=True
    )
    family_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("asset_families.id", ondelete="RESTRICT"), index=True
    )
    current_revision_id: Mapped[UUID | None] = mapped_column(nullable=True)
    archived: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), index=True
    )
    third_party: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false()
    )
    author: Mapped[str | None] = mapped_column(String(255))
    origin: Mapped[str | None] = mapped_column(String(255))
    license: Mapped[str | None] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(String(2048))
    usage_notes: Mapped[str | None] = mapped_column(Text)


class AssetRevision(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "asset_revisions"
    __table_args__ = (
        UniqueConstraint("asset_id", "number", name="uq_asset_revisions_number"),
        UniqueConstraint("asset_id", "id", name="uq_asset_revisions_identity"),
        CheckConstraint("number > 0", name="number_positive"),
        ForeignKeyConstraint(
            ["asset_id", "restored_from_revision_id"],
            ["asset_revisions.asset_id", "asset_revisions.id"],
            name="fk_asset_revisions_restored_from",
            ondelete="RESTRICT",
        ),
    )
    asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT"), index=True
    )
    number: Mapped[int] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(Text)
    restored_from_revision_id: Mapped[UUID | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
