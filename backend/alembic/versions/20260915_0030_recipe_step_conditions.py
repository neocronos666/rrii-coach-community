"""Condiciones positivas de pasos de receta.

Revision ID: 20260915_0030
Revises: 20260915_0029
"""

import sqlalchemy as sa
from alembic import op

revision = "20260915_0030"
down_revision = "20260915_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "recipe_steps", sa.Column("condition_definition_id", sa.UUID(), nullable=True)
    )
    op.add_column(
        "recipe_steps", sa.Column("condition_value_id", sa.UUID(), nullable=True)
    )
    op.create_foreign_key(
        "fk_recipe_steps_condition",
        "recipe_steps",
        "option_values",
        ["condition_definition_id", "condition_value_id"],
        ["definition_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        op.f("ck_recipe_steps_condition_complete"),
        "recipe_steps",
        "(condition_definition_id IS NULL) = (condition_value_id IS NULL)",
    )


def downgrade() -> None:
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM recipe_steps WHERE condition_value_id IS NOT NULL) THEN
            RAISE EXCEPTION 'Recetas condicionadas existentes: downgrade no permitido';
        END IF;
    END $$""")
    op.drop_constraint(
        op.f("ck_recipe_steps_condition_complete"), "recipe_steps", type_="check"
    )
    op.drop_constraint("fk_recipe_steps_condition", "recipe_steps", type_="foreignkey")
    op.drop_column("recipe_steps", "condition_value_id")
    op.drop_column("recipe_steps", "condition_definition_id")
