"""Materiales elegidos mediante opciones semánticas.

Revision ID: 20260925_0033
Revises: 20260923_0032
"""

import sqlalchemy as sa
from alembic import op

revision = "20260925_0033"
down_revision = "20260923_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("option_values", sa.Column("supply_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        op.f("fk_option_values_supply_id_supplies"),
        "option_values",
        "supplies",
        ["supply_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(op.f("ix_option_values_supply_id"), "option_values", ["supply_id"])
    op.create_table(
        "recipe_selected_supply_inputs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("step_id", sa.UUID(), nullable=False),
        sa.Column("definition_id", sa.UUID(), nullable=False),
        sa.Column("quantity_per_batch", sa.Numeric(18, 6), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recipe_selected_supply_inputs")),
        sa.ForeignKeyConstraint(["step_id"], ["recipe_steps.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["definition_id"], ["option_definitions.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint(
            "step_id", "definition_id", name="uq_recipe_selected_supply_definition"
        ),
        sa.CheckConstraint(
            "quantity_per_batch > 0",
            name=op.f("ck_recipe_selected_supply_inputs_quantity_positive"),
        ),
    )
    for column in ("step_id", "definition_id"):
        op.create_index(
            op.f(f"ix_recipe_selected_supply_inputs_{column}"),
            "recipe_selected_supply_inputs",
            [column],
        )


def downgrade() -> None:
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM recipe_selected_supply_inputs)
           OR EXISTS (SELECT 1 FROM option_values WHERE supply_id IS NOT NULL) THEN
            RAISE EXCEPTION 'Materiales existentes: downgrade no permitido';
        END IF;
    END $$""")
    op.drop_table("recipe_selected_supply_inputs")
    op.drop_index(op.f("ix_option_values_supply_id"), table_name="option_values")
    op.drop_constraint(
        op.f("fk_option_values_supply_id_supplies"), "option_values", type_="foreignkey"
    )
    op.drop_column("option_values", "supply_id")
