"""Puente único de Quick Quote y costo técnico de demanda.

Revision ID: 20260929_0037
Revises: 20260928_0036
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260929_0037"
down_revision: str | Sequence[str] | None = "20260928_0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cost_calculations",
        sa.Column("demand_quantity", sa.Numeric(18, 6), nullable=True),
    )
    op.add_column(
        "cost_calculations", sa.Column("demand_unit", sa.String(20), nullable=True)
    )
    op.create_check_constraint(
        op.f("ck_cost_calculations_demand_basis"),
        "cost_calculations",
        "(calculation_type = 'recipe_demand' AND demand_quantity IS NOT NULL "
        "AND demand_quantity > 0 AND demand_unit IS NOT NULL) OR "
        "(calculation_type <> 'recipe_demand' AND demand_quantity IS NULL "
        "AND demand_unit IS NULL)",
    )
    op.create_table(
        "quick_quote_formalizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("quick_quote_id", sa.Uuid(), nullable=False),
        sa.Column("source_revision_id", sa.Uuid(), nullable=False),
        sa.Column("quote_id", sa.Uuid(), nullable=False),
        sa.Column("cost_calculation_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("request_payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quick_quote_formalizations")),
        sa.ForeignKeyConstraint(
            ["quick_quote_id"],
            ["quick_quotes.id"],
            ondelete="RESTRICT",
            name=op.f("fk_quick_quote_formalizations_quick_quote_id_quick_quotes"),
        ),
        sa.ForeignKeyConstraint(
            ["source_revision_id"],
            ["quick_quote_revisions.id"],
            ondelete="RESTRICT",
            name=op.f(
                "fk_quick_quote_formalizations_source_revision_id_quick_quote_revisions"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["quote_id"],
            ["quotes.id"],
            ondelete="RESTRICT",
            name=op.f("fk_quick_quote_formalizations_quote_id_quotes"),
        ),
        sa.ForeignKeyConstraint(
            ["cost_calculation_id"],
            ["cost_calculations.id"],
            ondelete="RESTRICT",
            name=op.f(
                "fk_quick_quote_formalizations_cost_calculation_id_cost_calculations"
            ),
        ),
        sa.UniqueConstraint(
            "quick_quote_id", name=op.f("uq_quick_quote_formalizations_quick_quote_id")
        ),
        sa.UniqueConstraint(
            "source_revision_id",
            name=op.f("uq_quick_quote_formalizations_source_revision_id"),
        ),
        sa.UniqueConstraint(
            "quote_id", name=op.f("uq_quick_quote_formalizations_quote_id")
        ),
        sa.UniqueConstraint(
            "cost_calculation_id",
            name=op.f("uq_quick_quote_formalizations_cost_calculation_id"),
        ),
        sa.UniqueConstraint(
            "request_id", name=op.f("uq_quick_quote_formalizations_request_id")
        ),
    )


def downgrade() -> None:
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM quick_quote_formalizations) OR "
            "EXISTS (SELECT 1 FROM cost_calculations WHERE demand_quantity IS NOT NULL)"
        )
    ):
        raise RuntimeError("No se puede eliminar historia de formalización o demanda")
    op.drop_table("quick_quote_formalizations")
    op.drop_constraint(
        op.f("ck_cost_calculations_demand_basis"), "cost_calculations", type_="check"
    )
    op.drop_column("cost_calculations", "demand_unit")
    op.drop_column("cost_calculations", "demand_quantity")
