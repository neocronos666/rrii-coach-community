"""Borradores independientes y revisiones inmutables de Quick Quote.

Revision ID: 20260928_0036
Revises: 20260928_0035
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260928_0036"
down_revision: str | Sequence[str] | None = "20260928_0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "quick_quotes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("current_revision", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quick_quotes")),
        sa.CheckConstraint(
            "current_revision > 0", name=op.f("ck_quick_quotes_revision_positive")
        ),
    )
    op.create_table(
        "quick_quote_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("quick_quote_id", sa.Uuid(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("operation", sa.String(20), nullable=False),
        sa.Column("request_payload", postgresql.JSONB(), nullable=False),
        sa.Column("definition", postgresql.JSONB(), nullable=False),
        sa.Column("evaluation", postgresql.JSONB(), nullable=False),
        sa.Column("recipe_id", sa.Uuid(), nullable=False),
        sa.Column("variant_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quick_quote_revisions")),
        sa.ForeignKeyConstraint(
            ["quick_quote_id"],
            ["quick_quotes.id"],
            ondelete="RESTRICT",
            name=op.f("fk_quick_quote_revisions_quick_quote_id_quick_quotes"),
        ),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipes.id"],
            ondelete="RESTRICT",
            name=op.f("fk_quick_quote_revisions_recipe_id_recipes"),
        ),
        sa.ForeignKeyConstraint(
            ["variant_id"],
            ["product_variants.id"],
            ondelete="RESTRICT",
            name=op.f("fk_quick_quote_revisions_variant_id_product_variants"),
        ),
        sa.UniqueConstraint(
            "quick_quote_id",
            "revision",
            name=op.f("uq_quick_quote_revisions_quick_quote_id"),
        ),
        sa.UniqueConstraint(
            "request_id", name=op.f("uq_quick_quote_revisions_request_id")
        ),
        sa.CheckConstraint(
            "revision > 0", name=op.f("ck_quick_quote_revisions_revision_positive")
        ),
        sa.CheckConstraint(
            "operation IN ('create','replace','recalculate')",
            name=op.f("ck_quick_quote_revisions_operation_valid"),
        ),
    )
    op.create_index(
        op.f("ix_quick_quote_revisions_quick_quote_id"),
        "quick_quote_revisions",
        ["quick_quote_id"],
    )


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM quick_quotes)")):
        raise RuntimeError("No se puede eliminar historia de Quick Quote")
    op.drop_index(
        op.f("ix_quick_quote_revisions_quick_quote_id"),
        table_name="quick_quote_revisions",
    )
    op.drop_table("quick_quote_revisions")
    op.drop_table("quick_quotes")
