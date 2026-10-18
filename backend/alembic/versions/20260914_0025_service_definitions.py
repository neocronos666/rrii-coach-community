"""Catálogo de servicios humanos reutilizables

Revision ID: 20260914_0025
Revises: 20260914_0024
Create Date: 2026-09-14 17:39:06.545425
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260914_0025"
down_revision: str | Sequence[str] | None = "20260914_0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "service_definitions",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("action_template", sa.Text(), nullable=True),
        sa.Column(
            "active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(trim(name)) > 0", name=op.f("ck_service_definitions_name_nonempty")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_service_definitions")),
        sa.UniqueConstraint("name", name=op.f("uq_service_definitions_name")),
    )


def downgrade() -> None:
    op.drop_table("service_definitions")
