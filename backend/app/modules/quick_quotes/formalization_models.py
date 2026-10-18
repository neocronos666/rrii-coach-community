from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin


class QuickQuoteFormalization(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "quick_quote_formalizations"

    quick_quote_id: Mapped[UUID] = mapped_column(
        ForeignKey("quick_quotes.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    source_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("quick_quote_revisions.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    quote_id: Mapped[UUID] = mapped_column(
        ForeignKey("quotes.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    cost_calculation_id: Mapped[UUID] = mapped_column(
        ForeignKey("cost_calculations.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    request_id: Mapped[UUID] = mapped_column(unique=True, nullable=False)
    request_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
