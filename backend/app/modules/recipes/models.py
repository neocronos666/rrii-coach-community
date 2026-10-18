from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    false,
    text,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Recipe(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recipes"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="name_nonempty"),
        ForeignKeyConstraint(
            ["product_id", "product_variant_id"],
            ["product_variants.product_id", "product_variants.id"],
            name="fk_recipes_product_variant_identity",
            ondelete="RESTRICT",
        ),
        Index(
            "uq_recipes_product_base",
            "product_id",
            unique=True,
            postgresql_where=text("product_variant_id IS NULL"),
        ),
    )
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True
    )
    product_variant_id: Mapped[UUID | None] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())


class RecipeStep(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recipe_steps"
    __table_args__ = (
        ForeignKeyConstraint(
            ["condition_definition_id", "condition_value_id"],
            ["option_values.definition_id", "option_values.id"],
            name="fk_recipe_steps_condition",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "(condition_definition_id IS NULL) = (condition_value_id IS NULL)",
            name="condition_complete",
        ),
        CheckConstraint(
            "NOT scale_by_selection OR "
            "(condition_value_id IS NOT NULL AND NOT is_final_output)",
            name="selection_scale_valid",
        ),
        UniqueConstraint("recipe_id", "key", name="uq_recipe_steps_key"),
        UniqueConstraint("recipe_id", "id", name="uq_recipe_steps_identity"),
        CheckConstraint("quantity_per_output > 0", name="quantity_positive"),
        CheckConstraint("batch_yield > 0", name="batch_yield_positive"),
        CheckConstraint("position >= 0", name="position_nonnegative"),
        CheckConstraint(
            "kind IN ('operation', 'print', 'service', 'wait')", name="kind_valid"
        ),
        CheckConstraint(
            "(kind = 'service') = (service_definition_id IS NOT NULL)",
            name="service_reference",
        ),
        CheckConstraint(
            "jsonb_typeof(action_context) = 'object'", name="action_context_object"
        ),
    )
    recipe_id: Mapped[UUID] = mapped_column(
        ForeignKey("recipes.id", ondelete="RESTRICT"), index=True
    )
    key: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(255))
    condition_definition_id: Mapped[UUID | None] = mapped_column()
    condition_value_id: Mapped[UUID | None] = mapped_column()
    scale_by_selection: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false()
    )
    task_type: Mapped[str] = mapped_column(String(40))
    kind: Mapped[str] = mapped_column(
        String(20), default="operation", server_default="operation"
    )
    service_definition_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("service_definitions.id", ondelete="RESTRICT"), index=True
    )
    action_template: Mapped[str | None] = mapped_column(Text)
    action_context: Mapped[dict[str, str]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    unit: Mapped[str] = mapped_column(String(20))
    quantity_per_output: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    batch_yield: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    position: Mapped[int]
    is_final_output: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false()
    )
    output_variant_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("product_variants.id", ondelete="RESTRICT")
    )
    required_machine_type: Mapped[str | None] = mapped_column(String(50))
    instructions: Mapped[str | None] = mapped_column(Text)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class RecipeStepDependency(Base):
    __tablename__ = "recipe_step_dependencies"
    __table_args__ = (
        ForeignKeyConstraint(
            ["recipe_id", "step_id"],
            ["recipe_steps.recipe_id", "recipe_steps.id"],
            name="fk_recipe_dependencies_step",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["recipe_id", "depends_on_step_id"],
            ["recipe_steps.recipe_id", "recipe_steps.id"],
            name="fk_recipe_dependencies_prerequisite",
            ondelete="RESTRICT",
        ),
        CheckConstraint("step_id <> depends_on_step_id", name="not_self"),
    )
    recipe_id: Mapped[UUID] = mapped_column(primary_key=True)
    step_id: Mapped[UUID] = mapped_column(primary_key=True)
    depends_on_step_id: Mapped[UUID] = mapped_column(primary_key=True)


class RecipeSupplyInput(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "recipe_supply_inputs"
    __table_args__ = (
        UniqueConstraint(
            "step_id", "supply_id", name="uq_recipe_supply_inputs_resource"
        ),
        CheckConstraint("quantity_per_batch > 0", name="quantity_positive"),
    )
    step_id: Mapped[UUID] = mapped_column(
        ForeignKey("recipe_steps.id", ondelete="RESTRICT"), index=True
    )
    supply_id: Mapped[UUID] = mapped_column(
        ForeignKey("supplies.id", ondelete="RESTRICT"), index=True
    )
    quantity_per_batch: Mapped[Decimal] = mapped_column(Numeric(18, 6))


class RecipeProductInput(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "recipe_product_inputs"
    __table_args__ = (
        UniqueConstraint(
            "step_id", "product_variant_id", name="uq_recipe_product_inputs_resource"
        ),
        CheckConstraint("quantity_per_batch > 0", name="quantity_positive"),
    )
    step_id: Mapped[UUID] = mapped_column(
        ForeignKey("recipe_steps.id", ondelete="RESTRICT"), index=True
    )
    product_variant_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_variants.id", ondelete="RESTRICT"), index=True
    )
    quantity_per_batch: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    source_step_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("recipe_steps.id", ondelete="RESTRICT")
    )


class RecipeStepResource(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "recipe_step_resources"
    __table_args__ = (
        UniqueConstraint("step_id", "key", name="uq_recipe_step_resources_key"),
        ForeignKeyConstraint(
            ["selection_definition_id", "selection_value_id"],
            ["option_values.definition_id", "option_values.id"],
            name="fk_recipe_step_resources_selection",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "(asset_revision_id IS NOT NULL AND selection_definition_id IS NULL "
            "AND selection_value_id IS NULL) OR "
            "(asset_revision_id IS NULL AND selection_definition_id IS NOT NULL "
            "AND selection_value_id IS NOT NULL)",
            name="source_exclusive",
        ),
        CheckConstraint("quantity_per_batch > 0", name="quantity_positive"),
    )
    step_id: Mapped[UUID] = mapped_column(
        ForeignKey("recipe_steps.id", ondelete="RESTRICT"), index=True
    )
    key: Mapped[str] = mapped_column(String(80))
    selection_definition_id: Mapped[UUID | None] = mapped_column()
    selection_value_id: Mapped[UUID | None] = mapped_column()
    asset_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("asset_revisions.id", ondelete="RESTRICT"), index=True
    )
    quantity_per_batch: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    label: Mapped[str | None] = mapped_column(String(255))


class RecipeSelectedSupplyInput(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "recipe_selected_supply_inputs"
    __table_args__ = (
        UniqueConstraint(
            "step_id", "definition_id", name="uq_recipe_selected_supply_definition"
        ),
        CheckConstraint("quantity_per_batch > 0", name="quantity_positive"),
    )
    step_id: Mapped[UUID] = mapped_column(
        ForeignKey("recipe_steps.id", ondelete="RESTRICT"), index=True
    )
    definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("option_definitions.id", ondelete="RESTRICT"), index=True
    )
    quantity_per_batch: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    unit: Mapped[str] = mapped_column(String(20))
