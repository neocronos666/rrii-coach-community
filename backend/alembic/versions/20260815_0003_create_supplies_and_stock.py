"""Crear catálogo de insumos y ledger de stock.

Revision ID: 20260815_0003
Revises: 20260814_0002
Create Date: 2026-08-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260815_0003"
down_revision: str | Sequence[str] | None = "20260814_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column[object]]:
    return [
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
    ]


def upgrade() -> None:
    op.create_table(
        "supplies",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sku", sa.String(length=100), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("brand", sa.String(length=255), nullable=True),
        sa.Column("base_unit", sa.String(length=20), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_supplies")),
        sa.UniqueConstraint("sku", name=op.f("uq_supplies_sku")),
    )
    op.create_table(
        "supply_presentations",
        sa.Column("supply_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("purchase_price", sa.Numeric(precision=18, scale=4)),
        sa.Column("currency", sa.String(length=3)),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "purchase_price >= 0",
            name=op.f("ck_supply_presentations_purchase_price_nonnegative"),
        ),
        sa.CheckConstraint(
            "quantity > 0", name=op.f("ck_supply_presentations_quantity_positive")
        ),
        sa.ForeignKeyConstraint(
            ["supply_id"],
            ["supplies.id"],
            name=op.f("fk_supply_presentations_supply_id_supplies"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_supply_presentations")),
    )
    op.create_index(
        op.f("ix_supply_presentations_supply_id"),
        "supply_presentations",
        ["supply_id"],
        unique=False,
    )
    op.create_table(
        "supply_purchases",
        sa.Column("supply_id", sa.UUID(), nullable=False),
        sa.Column("presentation_id", sa.UUID(), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("total_cost", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("purchased_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("id", sa.UUID(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "quantity > 0", name=op.f("ck_supply_purchases_quantity_positive")
        ),
        sa.CheckConstraint(
            "total_cost >= 0",
            name=op.f("ck_supply_purchases_total_cost_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["presentation_id"],
            ["supply_presentations.id"],
            name=op.f("fk_supply_purchases_presentation_id_supply_presentations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["supply_id"],
            ["supplies.id"],
            name=op.f("fk_supply_purchases_supply_id_supplies"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_supply_purchases")),
    )
    op.create_index(
        op.f("ix_supply_purchases_presentation_id"),
        "supply_purchases",
        ["presentation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_supply_purchases_supply_id"),
        "supply_purchases",
        ["supply_id"],
        unique=False,
    )
    op.create_table(
        "supply_stock_movements",
        sa.Column("supply_id", sa.UUID(), nullable=False),
        sa.Column("movement_type", sa.String(length=30), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "movement_type IN ('purchase', 'adjustment_in', 'adjustment_out')",
            name=op.f("ck_supply_stock_movements_movement_type_valid"),
        ),
        sa.CheckConstraint(
            "quantity <> 0", name=op.f("ck_supply_stock_movements_quantity_nonzero")
        ),
        sa.ForeignKeyConstraint(
            ["supply_id"],
            ["supplies.id"],
            name=op.f("fk_supply_stock_movements_supply_id_supplies"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_supply_stock_movements")),
    )
    op.create_index(
        op.f("ix_supply_stock_movements_supply_id"),
        "supply_stock_movements",
        ["supply_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_supply_stock_movements_supply_id"), table_name="supply_stock_movements"
    )
    op.drop_table("supply_stock_movements")
    op.drop_index(op.f("ix_supply_purchases_supply_id"), table_name="supply_purchases")
    op.drop_index(
        op.f("ix_supply_purchases_presentation_id"), table_name="supply_purchases"
    )
    op.drop_table("supply_purchases")
    op.drop_index(
        op.f("ix_supply_presentations_supply_id"), table_name="supply_presentations"
    )
    op.drop_table("supply_presentations")
    op.drop_table("supplies")
