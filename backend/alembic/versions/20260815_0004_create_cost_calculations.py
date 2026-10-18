"""Crear snapshots de costos técnicos.

Revision ID: 20260815_0004
Revises: 20260815_0003
Create Date: 2026-08-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260815_0004"
down_revision: str | Sequence[str] | None = "20260815_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cost_calculations",
        sa.Column("calculation_type", sa.String(length=30), nullable=False),
        sa.Column("complete", sa.Boolean(), nullable=False),
        sa.Column("multi_currency", sa.Boolean(), nullable=False),
        sa.Column("warnings", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cost_calculations")),
    )
    op.create_table(
        "cost_calculation_lines",
        sa.Column("calculation_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("unit", sa.String(length=30), nullable=False),
        sa.Column("unit_cost", sa.Numeric(precision=24, scale=8), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("subtotal", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("source_reference", sa.String(length=255), nullable=True),
        sa.Column("complete", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.CheckConstraint(
            "quantity >= 0", name=op.f("ck_cost_calculation_lines_quantity_nonnegative")
        ),
        sa.CheckConstraint(
            "unit_cost >= 0",
            name=op.f("ck_cost_calculation_lines_unit_cost_nonnegative"),
        ),
        sa.CheckConstraint(
            "subtotal >= 0", name=op.f("ck_cost_calculation_lines_subtotal_nonnegative")
        ),
        sa.ForeignKeyConstraint(
            ["calculation_id"],
            ["cost_calculations.id"],
            name=op.f("fk_cost_calculation_lines_calculation_id_cost_calculations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cost_calculation_lines")),
    )
    op.create_index(
        op.f("ix_cost_calculation_lines_calculation_id"),
        "cost_calculation_lines",
        ["calculation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_cost_calculation_lines_calculation_id"),
        table_name="cost_calculation_lines",
    )
    op.drop_table("cost_calculation_lines")
    op.drop_table("cost_calculations")
