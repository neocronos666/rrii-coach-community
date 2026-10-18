"""Asignación física exclusivamente en planificación de producción

Revision ID: 20260914_0027
Revises: 20260914_0026
Create Date: 2026-09-14 22:53:03.234925
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260914_0027"
down_revision: str | Sequence[str] | None = "20260914_0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Retirar sólo la sugerencia de Recipe; no modificar tareas ni snapshots.
    op.drop_constraint(
        op.f("fk_recipe_steps_suggested_machine_id_machines"),
        "recipe_steps",
        type_="foreignkey",
    )
    op.drop_column("recipe_steps", "suggested_machine_id")


def downgrade() -> None:
    # Se recupera el esquema; las sugerencias retiradas no se pueden reconstruir.
    op.add_column(
        "recipe_steps",
        sa.Column(
            "suggested_machine_id", sa.UUID(), autoincrement=False, nullable=True
        ),
    )
    op.create_foreign_key(
        op.f("fk_recipe_steps_suggested_machine_id_machines"),
        "recipe_steps",
        "machines",
        ["suggested_machine_id"],
        ["id"],
        ondelete="RESTRICT",
    )
