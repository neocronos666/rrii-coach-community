from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin
from app.modules.orders.models import Order
from app.modules.projects.models import Project


class QuoteConversion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "quote_conversions"
    __table_args__ = (
        CheckConstraint(
            "(target_type = 'order' AND order_id IS NOT NULL AND project_id IS NULL) "
            "OR (target_type = 'project' AND project_id IS NOT NULL "
            "AND order_id IS NULL)",
            name="target_consistent",
        ),
    )

    quote_id: Mapped[UUID] = mapped_column(
        ForeignKey("quotes.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    order_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"), unique=True
    )
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="RESTRICT"), unique=True
    )
    converted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    order: Mapped[Order | None] = relationship()
    project: Mapped[Project | None] = relationship()
