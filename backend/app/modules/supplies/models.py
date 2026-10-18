from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Supply(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Recurso físico comprable, almacenable o consumible."""

    __tablename__ = "supplies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(100), unique=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(255))
    base_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    notes: Mapped[str | None] = mapped_column(Text)

    presentations: Mapped[list["SupplyPresentation"]] = relationship(
        back_populates="supply"
    )
    purchases: Mapped[list["SupplyPurchase"]] = relationship(back_populates="supply")
    movements: Mapped[list["SupplyStockMovement"]] = relationship(
        back_populates="supply"
    )


class SupplyPresentation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Presentación habitual de compra convertible a la unidad base."""

    __tablename__ = "supply_presentations"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("purchase_price >= 0", name="purchase_price_nonnegative"),
    )

    supply_id: Mapped[UUID] = mapped_column(
        ForeignKey("supplies.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    currency: Mapped[str | None] = mapped_column(String(3))
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )

    supply: Mapped[Supply] = relationship(back_populates="presentations")
    purchases: Mapped[list["SupplyPurchase"]] = relationship(
        back_populates="presentation"
    )


class SupplyPurchase(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Ingreso histórico con cantidad normalizada y costo total."""

    __tablename__ = "supply_purchases"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("total_cost >= 0", name="total_cost_nonnegative"),
    )

    supply_id: Mapped[UUID] = mapped_column(
        ForeignKey("supplies.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    presentation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("supply_presentations.id", ondelete="RESTRICT"), index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    purchased_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)

    supply: Mapped[Supply] = relationship(back_populates="purchases")
    presentation: Mapped[SupplyPresentation | None] = relationship(
        back_populates="purchases"
    )


class SupplyStockMovement(UUIDPrimaryKeyMixin, Base):
    """Entrada o salida inmutable del ledger de stock."""

    __tablename__ = "supply_stock_movements"
    __table_args__ = (
        CheckConstraint(
            "(movement_type = 'consumption' AND run_consumption_id IS NOT NULL "
            "AND quantity < 0) OR (movement_type <> 'consumption' "
            "AND run_consumption_id IS NULL)",
            name="consumption_link",
        ),
        CheckConstraint("quantity <> 0", name="quantity_nonzero"),
        CheckConstraint(
            "purchase_id IS NULL OR (movement_type = 'purchase' AND quantity > 0)",
            name="purchase_link",
        ),
        CheckConstraint(
            "movement_type IN ('purchase', 'adjustment_in', "
            "'adjustment_out', 'consumption')",
            name="movement_type_valid",
        ),
    )

    purchase_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("supply_purchases.id", ondelete="RESTRICT"), unique=True
    )
    run_consumption_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("production_run_supply_consumptions.id", ondelete="RESTRICT"),
        unique=True,
    )
    supply_id: Mapped[UUID] = mapped_column(
        ForeignKey("supplies.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    movement_type: Mapped[str] = mapped_column(String(30), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    supply: Mapped[Supply] = relationship(back_populates="movements")
