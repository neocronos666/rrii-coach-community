"""Miniatura única por revisión, conservada como archivo normalizado.

Revision ID: 20260930_0038
Revises: 20260929_0037
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260930_0038"
down_revision: str | Sequence[str] | None = "20260929_0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_asset_revision_files_role_valid"),
        "asset_revision_files",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_asset_revision_files_role_valid"),
        "asset_revision_files",
        "role IN ('manufacturing', 'source', 'documentation', "
        "'reference', 'media', 'thumbnail')",
    )
    op.create_index(
        "uq_asset_revision_files_thumbnail",
        "asset_revision_files",
        ["revision_id"],
        unique=True,
        postgresql_where=sa.text("role = 'thumbnail'"),
    )


def downgrade() -> None:
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM asset_revision_files "
            "WHERE role = 'thumbnail')"
        )
    ):
        raise RuntimeError(
            "No se puede retirar thumbnails mientras existan referencias"
        )
    op.drop_index(
        "uq_asset_revision_files_thumbnail", table_name="asset_revision_files"
    )
    op.drop_constraint(
        op.f("ck_asset_revision_files_role_valid"),
        "asset_revision_files",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_asset_revision_files_role_valid"),
        "asset_revision_files",
        "role IN ('manufacturing', 'source', 'documentation', 'reference', 'media')",
    )
