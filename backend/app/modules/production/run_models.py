from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ProductionRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "production_runs"
    __table_args__ = (
        CheckConstraint(
            "(task_id IS NOT NULL) <> (test_print_step_id IS NOT NULL)",
            name="origin_xor",
        ),
        Index(
            "uq_production_runs_open_test_step",
            "test_print_step_id",
            unique=True,
            postgresql_where=text("status = 'running'"),
        ),
        CheckConstraint("status IN ('running','closed')", name="status_valid"),
        CheckConstraint(
            "good_quantity >= 0 AND failed_quantity >= 0", name="quantities_nonnegative"
        ),
        CheckConstraint("actual_duration_seconds >= 0", name="duration_nonnegative"),
        CheckConstraint("ended_at >= started_at", name="chronological"),
        CheckConstraint(
            "(status = 'running' AND ended_at IS NULL AND good_quantity IS NULL "
            "AND failed_quantity IS NULL) OR (status = 'closed' "
            "AND ended_at IS NOT NULL "
            "AND good_quantity IS NOT NULL AND failed_quantity IS NOT NULL)",
            name="result_state",
        ),
        Index(
            "uq_production_runs_open_task",
            "task_id",
            unique=True,
            postgresql_where=text("status = 'running'"),
        ),
        Index(
            "uq_production_runs_open_machine",
            "machine_id",
            unique=True,
            postgresql_where=text("status = 'running' AND machine_id IS NOT NULL"),
        ),
    )
    test_print_step_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("test_print_steps.id", ondelete="RESTRICT"), index=True
    )
    task_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("production_tasks.id", ondelete="RESTRICT"), index=True
    )
    request_id: Mapped[UUID] = mapped_column(unique=True)
    request_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    machine_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("machines.id", ondelete="RESTRICT"), index=True
    )
    output_variant_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("product_variants.id", ondelete="RESTRICT"), index=True
    )
    unit: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="running")
    warnings: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    parameters: Mapped[dict[str, Any]] = mapped_column(JSONB)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    good_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    failed_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    actual_duration_seconds: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    failure_reason: Mapped[str | None] = mapped_column(String(40))
    notes: Mapped[str | None] = mapped_column(Text)
    result_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
