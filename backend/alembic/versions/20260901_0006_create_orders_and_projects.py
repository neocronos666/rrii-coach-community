"""Crear pedidos, proyectos y conversión operativa de presupuestos.

Revision ID: 20260901_0006
Revises: 20260815_0005
Create Date: 2026-09-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260901_0006"
down_revision: str | Sequence[str] | None = "20260815_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.schema.CreateSequence(sa.Sequence("order_code_sequence")))
    op.execute(sa.schema.CreateSequence(sa.Sequence("project_code_sequence")))
    op.create_table(
        "orders",
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("source_quote_id", sa.UUID(), nullable=False),
        sa.Column("source_quote_item_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("technical_unit_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("technical_total_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("quoted_suggested_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("quoted_final_price", sa.Numeric(18, 4), nullable=False),
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
            "status IN ('pending', 'cancelled')", name=op.f("ck_orders_status_valid")
        ),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_orders_quantity_positive")),
        sa.CheckConstraint(
            "technical_unit_cost >= 0",
            name=op.f("ck_orders_technical_unit_cost_nonnegative"),
        ),
        sa.CheckConstraint(
            "technical_total_cost >= 0",
            name=op.f("ck_orders_technical_total_cost_nonnegative"),
        ),
        sa.CheckConstraint(
            "quoted_suggested_price >= 0",
            name=op.f("ck_orders_suggested_price_nonnegative"),
        ),
        sa.CheckConstraint(
            "quoted_final_price >= 0", name=op.f("ck_orders_final_price_nonnegative")
        ),
        sa.ForeignKeyConstraint(
            ["source_quote_id"],
            ["quotes.id"],
            name=op.f("fk_orders_source_quote_id_quotes"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_quote_item_id"],
            ["quote_items.id"],
            name=op.f("fk_orders_source_quote_item_id_quote_items"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_orders")),
        sa.UniqueConstraint("code", name=op.f("uq_orders_code")),
        sa.UniqueConstraint("source_quote_id", name=op.f("uq_orders_source_quote_id")),
        sa.UniqueConstraint(
            "source_quote_item_id", name=op.f("uq_orders_source_quote_item_id")
        ),
    )
    op.create_table(
        "projects",
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("source_quote_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("quoted_technical_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("quoted_suggested_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("quoted_final_price", sa.Numeric(18, 4), nullable=False),
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
            "status IN ('pending', 'cancelled')", name=op.f("ck_projects_status_valid")
        ),
        sa.CheckConstraint(
            "quoted_technical_cost >= 0",
            name=op.f("ck_projects_technical_cost_nonnegative"),
        ),
        sa.CheckConstraint(
            "quoted_suggested_price >= 0",
            name=op.f("ck_projects_suggested_price_nonnegative"),
        ),
        sa.CheckConstraint(
            "quoted_final_price >= 0", name=op.f("ck_projects_final_price_nonnegative")
        ),
        sa.ForeignKeyConstraint(
            ["source_quote_id"],
            ["quotes.id"],
            name=op.f("fk_projects_source_quote_id_quotes"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_projects")),
        sa.UniqueConstraint("code", name=op.f("uq_projects_code")),
        sa.UniqueConstraint(
            "source_quote_id", name=op.f("uq_projects_source_quote_id")
        ),
    )
    op.create_table(
        "project_components",
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("source_quote_item_id", sa.UUID(), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("technical_unit_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("technical_total_cost", sa.Numeric(18, 4), nullable=False),
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
            "quantity > 0", name=op.f("ck_project_components_quantity_positive")
        ),
        sa.CheckConstraint(
            "technical_unit_cost >= 0",
            name=op.f("ck_project_components_technical_unit_cost_nonnegative"),
        ),
        sa.CheckConstraint(
            "technical_total_cost >= 0",
            name=op.f("ck_project_components_technical_total_cost_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_project_components_project_id_projects"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_quote_item_id"],
            ["quote_items.id"],
            name=op.f("fk_project_components_source_quote_item_id_quote_items"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_project_components")),
        sa.UniqueConstraint(
            "source_quote_item_id",
            name=op.f("uq_project_components_source_quote_item_id"),
        ),
    )
    op.create_index(
        op.f("ix_project_components_project_id"),
        "project_components",
        ["project_id"],
        unique=False,
    )
    op.create_table(
        "quote_conversions",
        sa.Column("quote_id", sa.UUID(), nullable=False),
        sa.Column("target_type", sa.String(length=20), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=True),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column(
            "converted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.CheckConstraint(
            "(target_type = 'order' AND order_id IS NOT NULL "
            "AND project_id IS NULL) OR (target_type = 'project' "
            "AND project_id IS NOT NULL AND order_id IS NULL)",
            name=op.f("ck_quote_conversions_target_consistent"),
        ),
        sa.ForeignKeyConstraint(
            ["quote_id"],
            ["quotes.id"],
            name=op.f("fk_quote_conversions_quote_id_quotes"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            name=op.f("fk_quote_conversions_order_id_orders"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_quote_conversions_project_id_projects"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quote_conversions")),
        sa.UniqueConstraint("quote_id", name=op.f("uq_quote_conversions_quote_id")),
        sa.UniqueConstraint("order_id", name=op.f("uq_quote_conversions_order_id")),
        sa.UniqueConstraint("project_id", name=op.f("uq_quote_conversions_project_id")),
    )


def downgrade() -> None:
    op.drop_table("quote_conversions")
    op.drop_index(
        op.f("ix_project_components_project_id"), table_name="project_components"
    )
    op.drop_table("project_components")
    op.drop_table("projects")
    op.drop_table("orders")
    op.execute(sa.schema.DropSequence(sa.Sequence("project_code_sequence")))
    op.execute(sa.schema.DropSequence(sa.Sequence("order_code_sequence")))
