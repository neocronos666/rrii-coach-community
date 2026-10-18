from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
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


class Project(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'cancelled')", name="status_valid"),
        CheckConstraint(
            "quoted_technical_cost >= 0", name="technical_cost_nonnegative"
        ),
        CheckConstraint(
            "quoted_suggested_price >= 0", name="suggested_price_nonnegative"
        ),
        CheckConstraint("quoted_final_price >= 0", name="final_price_nonnegative"),
    )

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    source_quote_id: Mapped[UUID] = mapped_column(
        ForeignKey("quotes.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    quoted_technical_cost: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False
    )
    quoted_suggested_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False
    )
    quoted_final_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    components: Mapped[list["ProjectComponent"]] = relationship(
        back_populates="project", order_by="ProjectComponent.position"
    )


class ProjectComponent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "project_components"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint(
            "technical_unit_cost >= 0", name="technical_unit_cost_nonnegative"
        ),
        CheckConstraint(
            "technical_total_cost >= 0", name="technical_total_cost_nonnegative"
        ),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_quote_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("quote_items.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    technical_unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    technical_total_cost: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    project: Mapped[Project] = relationship(back_populates="components")
