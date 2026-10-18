from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProductOption(Base):
    __tablename__ = "product_options"
    __table_args__ = (
        CheckConstraint("min_selections >= 0", name="minimum_nonnegative"),
        CheckConstraint(
            "max_selections IS NULL OR max_selections >= min_selections",
            name="range_valid",
        ),
        CheckConstraint(
            "context_asset_id IS NULL OR context_definition_id IS NULL",
            name="single_context",
        ),
        CheckConstraint(
            "context_definition_id IS NULL OR context_definition_id <> definition_id",
            name="not_self",
        ),
        ForeignKeyConstraint(
            ["product_id", "context_definition_id"],
            ["product_options.product_id", "product_options.definition_id"],
            name="fk_product_options_context",
            ondelete="RESTRICT",
        ),
    )
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), primary_key=True
    )
    definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("option_definitions.id", ondelete="RESTRICT"), primary_key=True
    )
    min_selections: Mapped[int]
    max_selections: Mapped[int | None]
    context_asset_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT")
    )
    context_definition_id: Mapped[UUID | None]


class ProductOptionValue(Base):
    __tablename__ = "product_option_values"
    __table_args__ = (
        ForeignKeyConstraint(
            ["product_id", "definition_id"],
            ["product_options.product_id", "product_options.definition_id"],
            name="fk_product_option_values_option",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["definition_id", "value_id"],
            ["option_values.definition_id", "option_values.id"],
            name="fk_product_option_values_value",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "default_quantity IS NULL OR default_quantity > 0", name="default_positive"
        ),
    )
    product_id: Mapped[UUID] = mapped_column(primary_key=True)
    definition_id: Mapped[UUID] = mapped_column(primary_key=True)
    value_id: Mapped[UUID] = mapped_column(primary_key=True)
    default_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
