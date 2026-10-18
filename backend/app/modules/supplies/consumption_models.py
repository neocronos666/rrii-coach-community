from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ProductionRunSupplyConsumption(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "production_run_supply_consumptions"
    __table_args__ = (
        UniqueConstraint("run_id", "supply_id", name="uq_run_supply_consumption"),
        CheckConstraint("consumed > 0", name="consumed_positive"),
        CheckConstraint("wasted >= 0 AND wasted <= consumed", name="wasted_subset"),
    )
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("production_runs.id", ondelete="RESTRICT"), index=True
    )
    supply_id: Mapped[UUID] = mapped_column(
        ForeignKey("supplies.id", ondelete="RESTRICT"), index=True
    )
    consumed: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    wasted: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    unit: Mapped[str] = mapped_column(String(20))
