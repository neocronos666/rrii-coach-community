"""asset_families_composition_compatibility

Revision ID: 20260913_0022
Revises: 20260913_0021
Create Date: 2026-09-13 22:12:46.951905
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260913_0022"
down_revision: str | Sequence[str] | None = "20260913_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "asset_families",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
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
            "length(trim(name)) > 0", name=op.f("ck_asset_families_name_nonempty")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_asset_families")),
    )
    op.create_index(
        op.f("ix_asset_families_name"), "asset_families", ["name"], unique=False
    )
    op.create_table(
        "asset_compatibilities",
        sa.Column("left_asset_id", sa.UUID(), nullable=False),
        sa.Column("right_asset_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "left_asset_id < right_asset_id",
            name=op.f("ck_asset_compatibilities_canonical_pair"),
        ),
        sa.ForeignKeyConstraint(
            ["left_asset_id"],
            ["assets.id"],
            name=op.f("fk_asset_compatibilities_left_asset_id_assets"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["right_asset_id"],
            ["assets.id"],
            name=op.f("fk_asset_compatibilities_right_asset_id_assets"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "left_asset_id", "right_asset_id", name=op.f("pk_asset_compatibilities")
        ),
    )
    op.create_index(
        op.f("ix_asset_compatibilities_right_asset_id"),
        "asset_compatibilities",
        ["right_asset_id"],
        unique=False,
    )
    op.create_table(
        "asset_composition_components",
        sa.Column("parent_revision_id", sa.UUID(), nullable=False),
        sa.Column("child_asset_id", sa.Uuid(), nullable=False),
        sa.Column("child_revision_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.CheckConstraint(
            "quantity > 0",
            name=op.f("ck_asset_composition_components_quantity_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["child_asset_id", "child_revision_id"],
            ["asset_revisions.asset_id", "asset_revisions.id"],
            name="fk_asset_composition_child_revision",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parent_revision_id"],
            ["asset_revisions.id"],
            name=op.f(
                "fk_asset_composition_components_parent_revision_id_asset_revisions"
            ),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_asset_composition_components")),
        sa.UniqueConstraint(
            "parent_revision_id", "child_asset_id", name="uq_asset_composition_child"
        ),
    )
    op.create_index(
        "ix_asset_composition_child_revision",
        "asset_composition_components",
        ["child_asset_id", "child_revision_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_asset_composition_components_parent_revision_id"),
        "asset_composition_components",
        ["parent_revision_id"],
        unique=False,
    )
    op.add_column("assets", sa.Column("family_id", sa.UUID(), nullable=True))
    op.create_index(op.f("ix_assets_family_id"), "assets", ["family_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_assets_family_id_asset_families"),
        "assets",
        "asset_families",
        ["family_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_assets_family_id_asset_families"), "assets", type_="foreignkey"
    )
    op.drop_index(op.f("ix_assets_family_id"), table_name="assets")
    op.drop_column("assets", "family_id")
    op.drop_index(
        op.f("ix_asset_composition_components_parent_revision_id"),
        table_name="asset_composition_components",
    )
    op.drop_index(
        "ix_asset_composition_child_revision", table_name="asset_composition_components"
    )
    op.drop_table("asset_composition_components")
    op.drop_index(
        op.f("ix_asset_compatibilities_right_asset_id"),
        table_name="asset_compatibilities",
    )
    op.drop_table("asset_compatibilities")
    op.drop_index(op.f("ix_asset_families_name"), table_name="asset_families")
    op.drop_table("asset_families")
