"""Escala explícita de demanda por selección.

Revision ID: 20260921_0031
Revises: 20260915_0030
"""

import sqlalchemy as sa
from alembic import op

revision = "20260921_0031"
down_revision = "20260915_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "recipe_steps",
        sa.Column(
            "scale_by_selection",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_check_constraint(
        op.f("ck_recipe_steps_selection_scale_valid"),
        "recipe_steps",
        "NOT scale_by_selection OR "
        "(condition_value_id IS NOT NULL AND NOT is_final_output)",
    )


def downgrade() -> None:
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM recipe_steps WHERE scale_by_selection) THEN
            RAISE EXCEPTION 'Escalas de selección existentes: downgrade no permitido';
        END IF;
    END $$""")
    op.drop_constraint(
        op.f("ck_recipe_steps_selection_scale_valid"), "recipe_steps", type_="check"
    )
    op.drop_column("recipe_steps", "scale_by_selection")
