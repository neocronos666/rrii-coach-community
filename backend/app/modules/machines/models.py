from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, Numeric, String, Text, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Machine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Equipo maker individual, sin asumir tecnología ni ubicación."""

    __tablename__ = "machines"
    __table_args__ = (
        CheckConstraint(
            "purchase_price >= 0",
            name="purchase_price_nonnegative",
        ),
        CheckConstraint(
            "rated_power_w >= 0",
            name="rated_power_w_nonnegative",
        ),
        CheckConstraint(
            "useful_life_hours >= 0",
            name="useful_life_hours_nonnegative",
        ),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    machine_type: Mapped[str] = mapped_column(String(50), nullable=False)
    manufacturer: Mapped[str | None] = mapped_column(String(255))
    model: Mapped[str | None] = mapped_column(String(255))
    purchase_date: Mapped[date | None] = mapped_column(Date)
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rated_power_w: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    useful_life_hours: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )
    notes: Mapped[str | None] = mapped_column(Text)
