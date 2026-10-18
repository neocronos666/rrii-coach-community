from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class TestPrint(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "test_prints"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open','completed','cancelled')", name="status_valid"
        ),
        CheckConstraint("target_quantity > 0", name="quantity_positive"),
    )
    recipe_id: Mapped[UUID] = mapped_column(
        ForeignKey("recipes.id", ondelete="RESTRICT")
    )
    variant_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_variants.id", ondelete="RESTRICT")
    )
    target_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    unit: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="open")
    request_id: Mapped[UUID] = mapped_column(unique=True)
    request_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)


class TestPrintStep(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "test_print_steps"
    __table_args__ = (
        UniqueConstraint("test_print_id", "key", name="uq_test_print_step_key"),
        CheckConstraint("planned_quantity > 0", name="quantity_positive"),
    )
    test_print_id: Mapped[UUID] = mapped_column(
        ForeignKey("test_prints.id", ondelete="RESTRICT"), index=True
    )
    key: Mapped[str] = mapped_column(String(80))
    planned_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    unit: Mapped[str] = mapped_column(String(30))
    output_variant_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("product_variants.id", ondelete="RESTRICT")
    )
    machine_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("machines.id", ondelete="RESTRICT")
    )
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)


class TestPrintAssetRevision(Base):
    __tablename__ = "test_print_asset_revisions"
    test_print_id: Mapped[UUID] = mapped_column(
        ForeignKey("test_prints.id", ondelete="RESTRICT"), primary_key=True
    )
    asset_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("asset_revisions.id", ondelete="RESTRICT"), primary_key=True
    )
