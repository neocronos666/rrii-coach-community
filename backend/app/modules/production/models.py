from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Sequence,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

production_task_code_sequence = Sequence("production_task_code_seq")


class ProductionTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "production_tasks"
    __table_args__ = (
        UniqueConstraint(
            "production_plan_id", "recipe_step_key", name="uq_production_plan_step"
        ),
        CheckConstraint(
            "(production_plan_id IS NULL AND recipe_step_key IS NULL) OR "
            "(production_plan_id IS NOT NULL AND recipe_step_key IS NOT NULL "
            "AND origin = 'recipe' AND recipe_id IS NOT NULL "
            "AND recipe_snapshot IS NOT NULL)",
            name="plan_origin_valid",
        ),
        CheckConstraint(
            "(order_id IS NOT NULL AND project_component_id IS NULL) OR "
            "(order_id IS NULL AND project_component_id IS NOT NULL)",
            name="origin_xor",
        ),
        CheckConstraint("planned_quantity > 0", name="planned_quantity_positive"),
        CheckConstraint(
            "execution_mode IN ('legacy','runs')", name="execution_mode_valid"
        ),
        CheckConstraint("origin IN ('manual','recipe')", name="origin_valid"),
        CheckConstraint(
            "task_type IN ('fdm_print','sla_print','cnc','laser',"
            "'postprocessing','assembly','manual','other')",
            name="task_type_valid",
        ),
        CheckConstraint(
            "status IN ('queued','in_progress','paused',"
            "'physically_completed','cancelled')",
            name="status_valid",
        ),
        CheckConstraint(
            "priority IN ('low','normal','high','urgent')", name="priority_valid"
        ),
        Index(
            "uq_production_tasks_machine_in_progress",
            "machine_id",
            unique=True,
            postgresql_where=text(
                "machine_id IS NOT NULL AND status = 'in_progress' "
                "AND execution_mode = 'legacy'"
            ),
        ),
    )
    production_plan_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("production_plans.id", ondelete="RESTRICT"), index=True
    )
    recipe_step_key: Mapped[str | None] = mapped_column(String(80))
    execution_mode: Mapped[str] = mapped_column(
        String(20), default="runs", server_default="runs"
    )
    origin: Mapped[str] = mapped_column(
        String(20), default="manual", server_default="manual"
    )
    output_variant_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("product_variants.id", ondelete="RESTRICT"), index=True
    )
    recipe_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("recipes.id", ondelete="RESTRICT"), index=True
    )
    recipe_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    order_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"), index=True
    )
    project_component_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("project_components.id", ondelete="RESTRICT"), index=True
    )
    task_type: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(30), default="queued", server_default="queued", index=True
    )
    priority: Mapped[str] = mapped_column(
        String(20), default="normal", server_default="normal"
    )
    planned_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    planned_unit: Mapped[str | None] = mapped_column(String(30))
    machine_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("machines.id", ondelete="RESTRICT"), index=True
    )
    queue_position: Mapped[int] = mapped_column(Integer, index=True)
    production_parameters: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}"
    )
    notes: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    physically_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProductionTaskDependency(Base):
    __tablename__ = "production_task_dependencies"
    __table_args__ = (
        CheckConstraint(
            "task_id <> depends_on_task_id",
            name="not_self_dependency",
        ),
    )

    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("production_tasks.id", ondelete="RESTRICT"), primary_key=True
    )
    depends_on_task_id: Mapped[UUID] = mapped_column(
        ForeignKey("production_tasks.id", ondelete="RESTRICT"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    prerequisite: Mapped[ProductionTask] = relationship(
        foreign_keys=[depends_on_task_id]
    )


class ProductionTaskAssetRevision(Base):
    """Raíces de revisiones usadas por una tarea, protegidas fuera del snapshot JSON."""

    __tablename__ = "production_task_asset_revisions"
    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("production_tasks.id", ondelete="RESTRICT"), primary_key=True
    )
    asset_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("asset_revisions.id", ondelete="RESTRICT"),
        primary_key=True,
        index=True,
    )
