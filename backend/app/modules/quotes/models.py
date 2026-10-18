from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Quote(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "quotes"
    __table_args__ = (
        CheckConstraint("markup_percentage >= 0", name="markup_nonnegative"),
        CheckConstraint("technical_cost_total >= 0", name="technical_cost_nonnegative"),
        CheckConstraint("suggested_price >= 0", name="suggested_price_nonnegative"),
        CheckConstraint("final_price >= 0", name="final_price_nonnegative"),
        CheckConstraint(
            "status IN ('draft', 'approved', 'rejected', 'expired')",
            name="status_valid",
        ),
    )

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    technical_cost_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False
    )
    markup_percentage: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    markup_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    subtotal_after_markup: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False
    )
    suggested_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    final_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    final_price_overridden: Mapped[bool] = mapped_column(Boolean, nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date)
    deposit_policy: Mapped[str] = mapped_column(String(20), nullable=False)
    deposit_type: Mapped[str | None] = mapped_column(String(20))
    deposit_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    deposit_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    notes: Mapped[str | None] = mapped_column(Text)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    items: Mapped[list["QuoteItem"]] = relationship(
        back_populates="quote",
        order_by="QuoteItem.position",
        cascade="all, delete-orphan",
    )
    adjustments: Mapped[list["QuoteAdjustment"]] = relationship(
        back_populates="quote",
        order_by="QuoteAdjustment.position",
        cascade="all, delete-orphan",
    )


class QuoteItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "quote_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("technical_unit_cost >= 0", name="unit_cost_nonnegative"),
        CheckConstraint("technical_total_cost >= 0", name="total_cost_nonnegative"),
    )

    quote_id: Mapped[UUID] = mapped_column(
        ForeignKey("quotes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    cost_calculation_id: Mapped[UUID] = mapped_column(
        ForeignKey("cost_calculations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    technical_unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    technical_total_cost: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    quote: Mapped[Quote] = relationship(back_populates="items")


class QuoteAdjustment(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "quote_adjustments"
    __table_args__ = (
        CheckConstraint("value >= 0", name="value_nonnegative"),
        CheckConstraint("amount >= 0", name="amount_nonnegative"),
        CheckConstraint(
            "adjustment_type IN ('surcharge', 'discount')", name="type_valid"
        ),
        CheckConstraint(
            "value_type IN ('fixed', 'percentage')", name="value_type_valid"
        ),
    )

    quote_id: Mapped[UUID] = mapped_column(
        ForeignKey("quotes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    adjustment_type: Mapped[str] = mapped_column(String(20), nullable=False)
    value_type: Mapped[str] = mapped_column(String(20), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    quote: Mapped[Quote] = relationship(back_populates="adjustments")
