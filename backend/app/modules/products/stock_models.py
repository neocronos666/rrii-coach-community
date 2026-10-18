from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ProductStockMovement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "product_stock_movements"
    __table_args__ = (
        CheckConstraint(
            "(movement_type IN ('production','purchase','adjustment_in','test_print') "
            "AND quantity > 0) "
            "OR (movement_type IN ('adjustment_out','consumption','delivery') "
            "AND quantity < 0)",
            name="type_quantity_valid",
        ),
        CheckConstraint(
            "(test_print_id IS NOT NULL AND movement_type = 'test_print' "
            "AND request_id IS NOT NULL AND run_id IS NULL "
            "AND run_consumption_id IS NULL AND allocation_id IS NULL) OR "
            "(test_print_id IS NULL AND ((movement_type = 'production' "
            "AND run_id IS NOT NULL "
            "AND request_id IS NULL AND run_consumption_id IS NULL "
            "AND allocation_id IS NULL) OR "
            "(movement_type = 'consumption' AND run_consumption_id IS NOT NULL "
            "AND run_id IS NULL AND request_id IS NULL AND allocation_id IS NULL) OR "
            "(movement_type = 'delivery' AND allocation_id IS NOT NULL "
            "AND request_id IS NOT NULL AND run_id IS NULL "
            "AND run_consumption_id IS NULL) OR "
            "(movement_type IN ('purchase','adjustment_in','adjustment_out') "
            "AND run_id IS NULL AND run_consumption_id IS NULL "
            "AND request_id IS NOT NULL AND allocation_id IS NULL)))",
            name="origin_valid",
        ),
    )
    variant_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_variants.id", ondelete="RESTRICT"), index=True
    )
    test_print_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("test_prints.id", ondelete="RESTRICT"), unique=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    unit: Mapped[str] = mapped_column(String(20))
    movement_type: Mapped[str] = mapped_column(String(30))
    run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("production_runs.id", ondelete="RESTRICT"), unique=True
    )
    request_id: Mapped[UUID | None] = mapped_column(unique=True)
    request_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    reason: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    run_consumption_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("production_run_product_consumptions.id", ondelete="RESTRICT"),
        unique=True,
    )

    allocation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("product_stock_allocations.id", ondelete="RESTRICT"), index=True
    )
