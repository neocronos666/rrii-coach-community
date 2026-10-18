"""asset_registry_and_revisions

Revision ID: 20260913_0020
Revises: 20260909_0019
Create Date: 2026-09-13 16:36:13.473354
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260913_0020"
down_revision: str | Sequence[str] | None = "20260909_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE asset_code_seq")
    op.create_table(
        "asset_categories",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("system_key", sa.String(length=40), nullable=True),
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
            "length(trim(name)) > 0", name=op.f("ck_asset_categories_name_nonempty")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_asset_categories")),
        sa.UniqueConstraint("name", name=op.f("uq_asset_categories_name")),
        sa.UniqueConstraint("system_key", name=op.f("uq_asset_categories_system_key")),
    )
    op.create_table(
        "assets",
        sa.Column(
            "code",
            sa.String(length=40),
            server_default=sa.text("'AST-' || nextval('asset_code_seq')::text"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category_id", sa.UUID(), nullable=False),
        sa.Column("current_revision_id", sa.Uuid(), nullable=True),
        sa.Column(
            "archived", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "third_party", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("origin", sa.String(length=255), nullable=True),
        sa.Column("license", sa.String(length=255), nullable=True),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("usage_notes", sa.Text(), nullable=True),
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
            "length(trim(name)) > 0", name=op.f("ck_assets_name_nonempty")
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["asset_categories.id"],
            name=op.f("fk_assets_category_id_asset_categories"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assets")),
        sa.UniqueConstraint("code", name=op.f("uq_assets_code")),
    )
    op.create_index(op.f("ix_assets_archived"), "assets", ["archived"], unique=False)
    op.create_index(
        op.f("ix_assets_category_id"), "assets", ["category_id"], unique=False
    )
    op.create_index(op.f("ix_assets_name"), "assets", ["name"], unique=False)
    op.create_table(
        "asset_revisions",
        sa.Column("asset_id", sa.UUID(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("restored_from_revision_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.CheckConstraint(
            "number > 0", name=op.f("ck_asset_revisions_number_positive")
        ),
        sa.ForeignKeyConstraint(
            ["asset_id", "restored_from_revision_id"],
            ["asset_revisions.asset_id", "asset_revisions.id"],
            name="fk_asset_revisions_restored_from",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
            name=op.f("fk_asset_revisions_asset_id_assets"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_asset_revisions")),
        sa.UniqueConstraint("asset_id", "id", name="uq_asset_revisions_identity"),
        sa.UniqueConstraint("asset_id", "number", name="uq_asset_revisions_number"),
    )
    op.create_index(
        op.f("ix_asset_revisions_asset_id"),
        "asset_revisions",
        ["asset_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_assets_current_revision",
        "assets",
        "asset_revisions",
        ["id", "current_revision_id"],
        ["asset_id", "id"],
        ondelete="RESTRICT",
    )
    op.execute(
        "INSERT INTO asset_categories (id, name, system_key) VALUES "
        "('124db5f7-f482-4ca2-91d4-7f35cadf36f6', 'Uncategorized', 'uncategorized')"
    )


def downgrade() -> None:
    op.drop_constraint("fk_assets_current_revision", "assets", type_="foreignkey")
    op.drop_index(op.f("ix_asset_revisions_asset_id"), table_name="asset_revisions")
    op.drop_table("asset_revisions")
    op.drop_index(op.f("ix_assets_name"), table_name="assets")
    op.drop_index(op.f("ix_assets_category_id"), table_name="assets")
    op.drop_index(op.f("ix_assets_archived"), table_name="assets")
    op.drop_table("assets")
    op.drop_table("asset_categories")
    op.execute("DROP SEQUENCE asset_code_seq")
