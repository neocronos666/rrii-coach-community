from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ProductionPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "production_plans"
    __table_args__ = (
        CheckConstraint(
            "(order_id IS NOT NULL) <> (project_component_id IS NOT NULL)",
            name="destination_xor",
        ),
        CheckConstraint("target_quantity > 0", name="quantity_positive"),
    )
    recipe_id: Mapped[UUID] = mapped_column(
        ForeignKey("recipes.id", ondelete="RESTRICT"), index=True
    )
    variant_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_variants.id", ondelete="RESTRICT")
    )
    order_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"), index=True
    )
    project_component_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("project_components.id", ondelete="RESTRICT"), index=True
    )
    allocation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("product_stock_allocations.id", ondelete="RESTRICT"), unique=True
    )
    target_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    request_id: Mapped[UUID] = mapped_column(unique=True)
    request_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
