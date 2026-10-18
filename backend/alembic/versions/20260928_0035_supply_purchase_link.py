"""Vincular nuevas compras al ledger sin inferir asociaciones históricas.

Revision ID: 20260928_0035
Revises: 20260926_0034
"""

import sqlalchemy as sa
from alembic import op

revision = "20260928_0035"
down_revision = "20260926_0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "supply_stock_movements", sa.Column("purchase_id", sa.Uuid(), nullable=True)
    )
    op.create_foreign_key(
        op.f("fk_supply_stock_movements_purchase_id_supply_purchases"),
        "supply_stock_movements",
        "supply_purchases",
        ["purchase_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        op.f("uq_supply_stock_movements_purchase_id"),
        "supply_stock_movements",
        ["purchase_id"],
    )
    op.create_check_constraint(
        op.f("ck_supply_stock_movements_purchase_link"),
        "supply_stock_movements",
        "purchase_id IS NULL OR (movement_type = 'purchase' AND quantity > 0)",
    )


def downgrade() -> None:
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM supply_stock_movements "
            "WHERE purchase_id IS NOT NULL)"
        )
    ):
        raise RuntimeError("No se puede eliminar la trazabilidad de compras existentes")
    op.drop_constraint(
        op.f("ck_supply_stock_movements_purchase_link"),
        "supply_stock_movements",
        type_="check",
    )
    op.drop_constraint(
        op.f("uq_supply_stock_movements_purchase_id"),
        "supply_stock_movements",
        type_="unique",
    )
    op.drop_constraint(
        op.f("fk_supply_stock_movements_purchase_id_supply_purchases"),
        "supply_stock_movements",
        type_="foreignkey",
    )
    op.drop_column("supply_stock_movements", "purchase_id")
