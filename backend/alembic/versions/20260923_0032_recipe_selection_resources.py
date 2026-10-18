"""Vinculación semántica de recursos de receta a opciones.

Revision ID: 20260923_0032
Revises: 20260921_0031
"""

import sqlalchemy as sa
from alembic import op

revision = "20260923_0032"
down_revision = "20260921_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("recipe_step_resources", "asset_revision_id", nullable=True)
    op.add_column(
        "recipe_step_resources", sa.Column("selection_definition_id", sa.Uuid())
    )
    op.add_column("recipe_step_resources", sa.Column("selection_value_id", sa.Uuid()))
    op.create_foreign_key(
        "fk_recipe_step_resources_selection",
        "recipe_step_resources",
        "option_values",
        ["selection_definition_id", "selection_value_id"],
        ["definition_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        op.f("ck_recipe_step_resources_source_exclusive"),
        "recipe_step_resources",
        "(asset_revision_id IS NOT NULL AND selection_definition_id IS NULL "
        "AND selection_value_id IS NULL) OR "
        "(asset_revision_id IS NULL AND selection_definition_id IS NOT NULL "
        "AND selection_value_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM recipe_step_resources
                   WHERE selection_value_id IS NOT NULL) THEN
            RAISE EXCEPTION 'Recursos dinámicos existentes: downgrade no permitido';
        END IF;
    END $$""")
    op.drop_constraint(
        op.f("ck_recipe_step_resources_source_exclusive"),
        "recipe_step_resources",
        type_="check",
    )
    op.drop_constraint(
        "fk_recipe_step_resources_selection",
        "recipe_step_resources",
        type_="foreignkey",
    )
    op.drop_column("recipe_step_resources", "selection_value_id")
    op.drop_column("recipe_step_resources", "selection_definition_id")
    op.alter_column("recipe_step_resources", "asset_revision_id", nullable=False)
