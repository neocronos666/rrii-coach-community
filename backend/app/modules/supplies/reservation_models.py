from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class SupplyReservation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "supply_reservations"
    __table_args__ = (
        UniqueConstraint(
            "task_id", "supply_id", name="uq_supply_reservations_task_supply"
        ),
        CheckConstraint("quantity >= 0", name="quantity_nonnegative"),
    )
    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("production_tasks.id", ondelete="RESTRICT"), index=True
    )
    supply_id: Mapped[UUID] = mapped_column(
        ForeignKey("supplies.id", ondelete="RESTRICT"), index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    unit: Mapped[str] = mapped_column(String(20))
