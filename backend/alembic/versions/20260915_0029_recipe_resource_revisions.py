"""Recursos fijados por paso y referencias históricas de producción

Revision ID: 20260915_0029
Revises: 20260914_0028
Create Date: 2026-09-15 16:26:42.078684
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260915_0029"
down_revision: str | Sequence[str] | None = "20260914_0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recipe_step_resources",
        sa.Column("step_id", sa.UUID(), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("asset_revision_id", sa.UUID(), nullable=False),
        sa.Column(
            "quantity_per_batch", sa.Numeric(precision=18, scale=6), nullable=False
        ),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.CheckConstraint(
            "quantity_per_batch > 0",
            name=op.f("ck_recipe_step_resources_quantity_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["asset_revision_id"],
            ["asset_revisions.id"],
            name=op.f("fk_recipe_step_resources_asset_revision_id_asset_revisions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["step_id"],
            ["recipe_steps.id"],
            name=op.f("fk_recipe_step_resources_step_id_recipe_steps"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recipe_step_resources")),
        sa.UniqueConstraint("step_id", "key", name="uq_recipe_step_resources_key"),
    )
    op.create_index(
        op.f("ix_recipe_step_resources_asset_revision_id"),
        "recipe_step_resources",
        ["asset_revision_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_recipe_step_resources_step_id"),
        "recipe_step_resources",
        ["step_id"],
        unique=False,
    )
    op.create_table(
        "production_task_asset_revisions",
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("asset_revision_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["asset_revision_id"],
            ["asset_revisions.id"],
            name=op.f(
                "fk_production_task_asset_revisions_asset_revision_id_asset_revisions"
            ),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["production_tasks.id"],
            name=op.f("fk_production_task_asset_revisions_task_id_production_tasks"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "task_id",
            "asset_revision_id",
            name=op.f("pk_production_task_asset_revisions"),
        ),
    )
    op.create_index(
        op.f("ix_production_task_asset_revisions_asset_revision_id"),
        "production_task_asset_revisions",
        ["asset_revision_id"],
        unique=False,
    )


def downgrade() -> None:
    # No perder referencias de recetas o historia para forzar el esquema anterior.
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM recipe_step_resources)
           OR EXISTS (SELECT 1 FROM production_task_asset_revisions) THEN
            RAISE EXCEPTION 'Referencias a recursos existentes: downgrade no permitido';
        END IF;
    END $$""")
    op.drop_index(
        op.f("ix_production_task_asset_revisions_asset_revision_id"),
        table_name="production_task_asset_revisions",
    )
    op.drop_table("production_task_asset_revisions")
    op.drop_index(
        op.f("ix_recipe_step_resources_step_id"), table_name="recipe_step_resources"
    )
    op.drop_index(
        op.f("ix_recipe_step_resources_asset_revision_id"),
        table_name="recipe_step_resources",
    )
    op.drop_table("recipe_step_resources")
