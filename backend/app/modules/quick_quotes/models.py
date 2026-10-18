from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class QuickQuote(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "quick_quotes"
    __table_args__ = (
        CheckConstraint("current_revision > 0", name="revision_positive"),
    )

    current_revision: Mapped[int] = mapped_column(Integer, nullable=False)


class QuickQuoteRevision(UUIDPrimaryKeyMixin, Base):
    """Revisión inmutable del borrador y de su evaluación explícita."""

    __tablename__ = "quick_quote_revisions"
    __table_args__ = (
        UniqueConstraint("quick_quote_id", "revision"),
        CheckConstraint("revision > 0", name="revision_positive"),
        CheckConstraint(
            "operation IN ('create','replace','recalculate')", name="operation_valid"
        ),
    )

    quick_quote_id: Mapped[UUID] = mapped_column(
        ForeignKey("quick_quotes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    request_id: Mapped[UUID] = mapped_column(unique=True, nullable=False)
    operation: Mapped[str] = mapped_column(String(20), nullable=False)
    request_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    definition: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    evaluation: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    recipe_id: Mapped[UUID] = mapped_column(
        ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=False
    )
    variant_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
