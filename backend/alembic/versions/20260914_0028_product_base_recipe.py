"""Receta base de Product y salida final parametrizada

Revision ID: 20260914_0028
Revises: 20260914_0027
Create Date: 2026-09-14 23:33:31.750465
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260914_0028"
down_revision: str | Sequence[str] | None = "20260914_0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_product_variants_identity", "product_variants", ["product_id", "id"]
    )
    op.add_column(
        "recipe_steps",
        sa.Column(
            "is_final_output",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column("recipes", sa.Column("product_id", sa.UUID(), nullable=True))
    op.execute(
        "UPDATE recipes SET product_id = product_variants.product_id "
        "FROM product_variants WHERE recipes.product_variant_id = product_variants.id"
    )
    op.alter_column("recipes", "product_id", existing_type=sa.UUID(), nullable=False)
    op.alter_column(
        "recipes", "product_variant_id", existing_type=sa.UUID(), nullable=True
    )
    op.create_index(
        op.f("ix_recipes_product_id"), "recipes", ["product_id"], unique=False
    )
    op.create_index(
        "uq_recipes_product_base",
        "recipes",
        ["product_id"],
        unique=True,
        postgresql_where=sa.text("product_variant_id IS NULL"),
    )
    op.drop_constraint(
        op.f("fk_recipes_product_variant_id_product_variants"),
        "recipes",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_recipes_product_variant_identity",
        "recipes",
        "product_variants",
        ["product_id", "product_variant_id"],
        ["product_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        op.f("fk_recipes_product_id_products"),
        "recipes",
        "products",
        ["product_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    # No convertir ni borrar recetas base para forzar un esquema anterior.
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM recipes WHERE product_variant_id IS NULL) THEN
            RAISE EXCEPTION 'Recetas base existentes: downgrade no permitido';
        END IF;
    END $$""")
    op.drop_constraint(
        op.f("fk_recipes_product_id_products"), "recipes", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_recipes_product_variant_identity", "recipes", type_="foreignkey"
    )
    op.create_foreign_key(
        op.f("fk_recipes_product_variant_id_product_variants"),
        "recipes",
        "product_variants",
        ["product_variant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_index(
        "uq_recipes_product_base",
        table_name="recipes",
        postgresql_where=sa.text("product_variant_id IS NULL"),
    )
    op.drop_index(op.f("ix_recipes_product_id"), table_name="recipes")
    op.alter_column(
        "recipes", "product_variant_id", existing_type=sa.UUID(), nullable=False
    )
    op.drop_column("recipes", "product_id")
    op.drop_column("recipe_steps", "is_final_output")
    op.drop_constraint(
        "uq_product_variants_identity", "product_variants", type_="unique"
    )
