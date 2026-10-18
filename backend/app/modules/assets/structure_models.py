from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AssetFamily(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "asset_families"
    __table_args__ = (CheckConstraint("length(trim(name)) > 0", name="name_nonempty"),)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text)


class AssetCompositionComponent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "asset_composition_components"
    __table_args__ = (
        UniqueConstraint(
            "parent_revision_id", "child_asset_id", name="uq_asset_composition_child"
        ),
        ForeignKeyConstraint(
            ["child_asset_id", "child_revision_id"],
            ["asset_revisions.asset_id", "asset_revisions.id"],
            name="fk_asset_composition_child_revision",
            ondelete="RESTRICT",
        ),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        Index(
            "ix_asset_composition_child_revision", "child_asset_id", "child_revision_id"
        ),
    )
    parent_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("asset_revisions.id", ondelete="RESTRICT"), index=True
    )
    child_asset_id: Mapped[UUID] = mapped_column()
    child_revision_id: Mapped[UUID] = mapped_column()
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6))


class AssetCompatibility(Base):
    __tablename__ = "asset_compatibilities"
    __table_args__ = (
        CheckConstraint("left_asset_id < right_asset_id", name="canonical_pair"),
    )
    left_asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT"), primary_key=True
    )
    right_asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
