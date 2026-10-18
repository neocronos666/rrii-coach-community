"""asset_revision_files

Revision ID: 20260913_0021
Revises: 20260913_0020
Create Date: 2026-09-13 20:33:22.995524
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260913_0021"
down_revision: str | Sequence[str] | None = "20260913_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stored_files",
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("detected_mime", sa.String(length=127), nullable=False),
        sa.Column("storage_key", sa.String(length=80), nullable=False),
        sa.Column(
            "technical_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.CheckConstraint(
            "sha256 ~ '^[0-9a-f]{64}$'", name=op.f("ck_stored_files_sha256_format")
        ),
        sa.CheckConstraint(
            "size_bytes > 0", name=op.f("ck_stored_files_size_positive")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stored_files")),
        sa.UniqueConstraint("sha256", name=op.f("uq_stored_files_sha256")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_stored_files_storage_key")),
    )
    op.create_table(
        "asset_revision_files",
        sa.Column("revision_id", sa.UUID(), nullable=False),
        sa.Column("stored_file_id", sa.UUID(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column(
            "attached_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.CheckConstraint(
            "role IN ('manufacturing', 'source', 'documentation', "
            "'reference', 'media')",
            name=op.f("ck_asset_revision_files_role_valid"),
        ),
        sa.CheckConstraint(
            "length(trim(filename)) > 0",
            name=op.f("ck_asset_revision_files_filename_nonempty"),
        ),
        sa.ForeignKeyConstraint(
            ["revision_id"],
            ["asset_revisions.id"],
            name=op.f("fk_asset_revision_files_revision_id_asset_revisions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["stored_file_id"],
            ["stored_files.id"],
            name=op.f("fk_asset_revision_files_stored_file_id_stored_files"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_asset_revision_files")),
        sa.UniqueConstraint(
            "revision_id", "filename", name="uq_asset_revision_files_name"
        ),
    )
    op.create_index(
        op.f("ix_asset_revision_files_revision_id"),
        "asset_revision_files",
        ["revision_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_asset_revision_files_stored_file_id"),
        "asset_revision_files",
        ["stored_file_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_asset_revision_files_stored_file_id"),
        table_name="asset_revision_files",
    )
    op.drop_index(
        op.f("ix_asset_revision_files_revision_id"), table_name="asset_revision_files"
    )
    op.drop_table("asset_revision_files")
    op.drop_table("stored_files")
