"""Configuración de características por producto

Revision ID: 20260914_0024
Revises: 20260914_0023
Create Date: 2026-09-14 16:54:01.431622
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260914_0024"
down_revision: str | Sequence[str] | None = "20260914_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_options",
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("definition_id", sa.UUID(), nullable=False),
        sa.Column("min_selections", sa.Integer(), nullable=False),
        sa.Column("max_selections", sa.Integer(), nullable=True),
        sa.Column("context_asset_id", sa.UUID(), nullable=True),
        sa.Column("context_definition_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "context_asset_id IS NULL OR context_definition_id IS NULL",
            name=op.f("ck_product_options_single_context"),
        ),
        sa.CheckConstraint(
            "context_definition_id IS NULL OR context_definition_id <> definition_id",
            name=op.f("ck_product_options_not_self"),
        ),
        sa.CheckConstraint(
            "max_selections IS NULL OR max_selections >= min_selections",
            name=op.f("ck_product_options_range_valid"),
        ),
        sa.CheckConstraint(
            "min_selections >= 0", name=op.f("ck_product_options_minimum_nonnegative")
        ),
        sa.ForeignKeyConstraint(
            ["context_asset_id"],
            ["assets.id"],
            name=op.f("fk_product_options_context_asset_id_assets"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["definition_id"],
            ["option_definitions.id"],
            name=op.f("fk_product_options_definition_id_option_definitions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["product_id", "context_definition_id"],
            ["product_options.product_id", "product_options.definition_id"],
            name="fk_product_options_context",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_product_options_product_id_products"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "product_id", "definition_id", name=op.f("pk_product_options")
        ),
    )
    op.create_table(
        "product_option_values",
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("definition_id", sa.Uuid(), nullable=False),
        sa.Column("value_id", sa.Uuid(), nullable=False),
        sa.Column("default_quantity", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.CheckConstraint(
            "default_quantity IS NULL OR default_quantity > 0",
            name=op.f("ck_product_option_values_default_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["definition_id", "value_id"],
            ["option_values.definition_id", "option_values.id"],
            name="fk_product_option_values_value",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["product_id", "definition_id"],
            ["product_options.product_id", "product_options.definition_id"],
            name="fk_product_option_values_option",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "product_id",
            "definition_id",
            "value_id",
            name=op.f("pk_product_option_values"),
        ),
    )


def downgrade() -> None:
    op.drop_table("product_option_values")
    op.drop_table("product_options")
