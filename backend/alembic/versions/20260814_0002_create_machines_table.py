"""Crear tabla machines.

Revision ID: 20260814_0002
Revises: 20260728_0001
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260814_0002"
down_revision: str | Sequence[str] | None = "20260728_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "machines",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("machine_type", sa.String(length=50), nullable=False),
        sa.Column("manufacturer", sa.String(length=255), nullable=True),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column("purchase_price", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("rated_power_w", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column(
            "useful_life_hours",
            sa.Numeric(precision=12, scale=2),
            nullable=True,
        ),
        sa.Column(
            "active",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
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
            "purchase_price >= 0",
            name=op.f("ck_machines_purchase_price_nonnegative"),
        ),
        sa.CheckConstraint(
            "rated_power_w >= 0",
            name=op.f("ck_machines_rated_power_w_nonnegative"),
        ),
        sa.CheckConstraint(
            "useful_life_hours >= 0",
            name=op.f("ck_machines_useful_life_hours_nonnegative"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_machines")),
    )


def downgrade() -> None:
    op.drop_table("machines")
