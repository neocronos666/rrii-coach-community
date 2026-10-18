from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ProductStockAllocation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "product_stock_allocations"
    __table_args__ = (
        CheckConstraint(
            "(order_id IS NOT NULL) <> (project_component_id IS NOT NULL)",
            name="destination_xor",
        ),
        CheckConstraint(
            "quantity >= 0 AND quantity <= initial_quantity AND initial_quantity > 0",
            name="quantity_valid",
        ),
    )
    variant_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_variants.id", ondelete="RESTRICT"), index=True
    )
    order_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"), index=True
    )
    project_component_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("project_components.id", ondelete="RESTRICT"), index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    initial_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    unit: Mapped[str] = mapped_column(String(20))
    request_id: Mapped[UUID] = mapped_column(unique=True)
    request_payload: Mapped[dict[str, object]] = mapped_column(JSONB)
