"""Tipos semánticos de paso y servicios reutilizables

Revision ID: 20260914_0026
Revises: 20260914_0025
Create Date: 2026-09-14 18:31:43.101119
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260914_0026"
down_revision: str | Sequence[str] | None = "20260914_0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "recipe_steps",
        sa.Column(
            "kind", sa.String(length=20), server_default="operation", nullable=False
        ),
    )
    op.add_column(
        "recipe_steps", sa.Column("service_definition_id", sa.UUID(), nullable=True)
    )
    op.add_column(
        "recipe_steps", sa.Column("action_template", sa.Text(), nullable=True)
    )
    op.add_column(
        "recipe_steps",
        sa.Column(
            "action_context",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.create_index(
        op.f("ix_recipe_steps_service_definition_id"),
        "recipe_steps",
        ["service_definition_id"],
        unique=False,
    )
    op.create_foreign_key(
        op.f("fk_recipe_steps_service_definition_id_service_definitions"),
        "recipe_steps",
        "service_definitions",
        ["service_definition_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.execute(
        "UPDATE recipe_steps SET kind = 'print' "
        "WHERE task_type IN ('fdm_print', 'sla_print')"
    )
    op.create_check_constraint(
        op.f("ck_recipe_steps_kind_valid"),
        "recipe_steps",
        "kind IN ('operation', 'print', 'service', 'wait')",
    )
    op.create_check_constraint(
        op.f("ck_recipe_steps_service_reference"),
        "recipe_steps",
        "(kind = 'service') = (service_definition_id IS NOT NULL)",
    )
    op.create_check_constraint(
        op.f("ck_recipe_steps_action_context_object"),
        "recipe_steps",
        "jsonb_typeof(action_context) = 'object'",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_recipe_steps_action_context_object"), "recipe_steps", type_="check"
    )
    op.drop_constraint(
        op.f("ck_recipe_steps_service_reference"), "recipe_steps", type_="check"
    )
    op.drop_constraint(
        op.f("ck_recipe_steps_kind_valid"), "recipe_steps", type_="check"
    )
    op.drop_constraint(
        op.f("fk_recipe_steps_service_definition_id_service_definitions"),
        "recipe_steps",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_recipe_steps_service_definition_id"), table_name="recipe_steps"
    )
    op.drop_column("recipe_steps", "action_context")
    op.drop_column("recipe_steps", "action_template")
    op.drop_column("recipe_steps", "service_definition_id")
    op.drop_column("recipe_steps", "kind")
