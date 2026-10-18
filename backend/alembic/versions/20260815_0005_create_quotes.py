"""Crear presupuestos y snapshots comerciales.

Revision ID: 20260815_0005
Revises: 20260815_0004
Create Date: 2026-08-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260815_0005"
down_revision: str | Sequence[str] | None = "20260815_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.schema.CreateSequence(sa.Sequence("quote_code_sequence")))
    op.create_table(
        "quotes",
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("technical_cost_total", sa.Numeric(18, 4), nullable=False),
        sa.Column("markup_percentage", sa.Numeric(12, 4), nullable=False),
        sa.Column("markup_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("subtotal_after_markup", sa.Numeric(18, 4), nullable=False),
        sa.Column("suggested_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("final_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("final_price_overridden", sa.Boolean(), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("deposit_policy", sa.String(length=20), nullable=False),
        sa.Column("deposit_type", sa.String(length=20), nullable=True),
        sa.Column("deposit_value", sa.Numeric(18, 4), nullable=True),
        sa.Column("deposit_amount", sa.Numeric(18, 4), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
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
            "markup_percentage >= 0", name=op.f("ck_quotes_markup_nonnegative")
        ),
        sa.CheckConstraint(
            "technical_cost_total >= 0",
            name=op.f("ck_quotes_technical_cost_nonnegative"),
        ),
        sa.CheckConstraint(
            "suggested_price >= 0", name=op.f("ck_quotes_suggested_price_nonnegative")
        ),
        sa.CheckConstraint(
            "final_price >= 0", name=op.f("ck_quotes_final_price_nonnegative")
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'approved', 'rejected', 'expired')",
            name=op.f("ck_quotes_status_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quotes")),
        sa.UniqueConstraint("code", name=op.f("uq_quotes_code")),
    )
    op.create_table(
        "quote_items",
        sa.Column("quote_id", sa.UUID(), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("cost_calculation_id", sa.UUID(), nullable=False),
        sa.Column("technical_unit_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("technical_total_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.CheckConstraint(
            "quantity > 0", name=op.f("ck_quote_items_quantity_positive")
        ),
        sa.CheckConstraint(
            "technical_unit_cost >= 0",
            name=op.f("ck_quote_items_unit_cost_nonnegative"),
        ),
        sa.CheckConstraint(
            "technical_total_cost >= 0",
            name=op.f("ck_quote_items_total_cost_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["cost_calculation_id"],
            ["cost_calculations.id"],
            name=op.f("fk_quote_items_cost_calculation_id_cost_calculations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["quote_id"],
            ["quotes.id"],
            name=op.f("fk_quote_items_quote_id_quotes"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quote_items")),
    )
    op.create_index(
        op.f("ix_quote_items_cost_calculation_id"),
        "quote_items",
        ["cost_calculation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_quote_items_quote_id"), "quote_items", ["quote_id"], unique=False
    )
    op.create_table(
        "quote_adjustments",
        sa.Column("quote_id", sa.UUID(), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("adjustment_type", sa.String(length=20), nullable=False),
        sa.Column("value_type", sa.String(length=20), nullable=False),
        sa.Column("value", sa.Numeric(18, 4), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.CheckConstraint(
            "value >= 0", name=op.f("ck_quote_adjustments_value_nonnegative")
        ),
        sa.CheckConstraint(
            "amount >= 0", name=op.f("ck_quote_adjustments_amount_nonnegative")
        ),
        sa.CheckConstraint(
            "adjustment_type IN ('surcharge', 'discount')",
            name=op.f("ck_quote_adjustments_type_valid"),
        ),
        sa.CheckConstraint(
            "value_type IN ('fixed', 'percentage')",
            name=op.f("ck_quote_adjustments_value_type_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["quote_id"],
            ["quotes.id"],
            name=op.f("fk_quote_adjustments_quote_id_quotes"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quote_adjustments")),
    )
    op.create_index(
        op.f("ix_quote_adjustments_quote_id"),
        "quote_adjustments",
        ["quote_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_quote_adjustments_quote_id"), table_name="quote_adjustments")
    op.drop_table("quote_adjustments")
    op.drop_index(op.f("ix_quote_items_quote_id"), table_name="quote_items")
    op.drop_index(op.f("ix_quote_items_cost_calculation_id"), table_name="quote_items")
    op.drop_table("quote_items")
    op.drop_table("quotes")
    op.execute(sa.schema.DropSequence(sa.Sequence("quote_code_sequence")))
