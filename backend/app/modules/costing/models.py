from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin


class CostCalculation(UUIDPrimaryKeyMixin, Base):
    """Snapshot inmutable de un costo técnico."""

    __tablename__ = "cost_calculations"
    __table_args__ = (
        CheckConstraint(
            "(calculation_type = 'recipe_demand' AND demand_quantity IS NOT NULL "
            "AND demand_quantity > 0 AND demand_unit IS NOT NULL) OR "
            "(calculation_type <> 'recipe_demand' AND demand_quantity IS NULL "
            "AND demand_unit IS NULL)",
            name="demand_basis",
        ),
    )

    demand_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    demand_unit: Mapped[str | None] = mapped_column(String(20))

    calculation_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="technical"
    )
    complete: Mapped[bool] = mapped_column(Boolean, nullable=False)
    multi_currency: Mapped[bool] = mapped_column(Boolean, nullable=False)
    warnings: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    lines: Mapped[list["CostCalculationLine"]] = relationship(
        back_populates="calculation",
        order_by="CostCalculationLine.position",
        cascade="all, delete-orphan",
    )


class CostCalculationLine(UUIDPrimaryKeyMixin, Base):
    """Línea congelada con fuente y valor económico usados."""

    __tablename__ = "cost_calculation_lines"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="quantity_nonnegative"),
        CheckConstraint("unit_cost >= 0", name="unit_cost_nonnegative"),
        CheckConstraint("subtotal >= 0", name="subtotal_nonnegative"),
    )

    calculation_id: Mapped[UUID] = mapped_column(
        ForeignKey("cost_calculations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    currency: Mapped[str | None] = mapped_column(String(3))
    subtotal: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(255))
    complete: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    calculation: Mapped[CostCalculation] = relationship(back_populates="lines")
