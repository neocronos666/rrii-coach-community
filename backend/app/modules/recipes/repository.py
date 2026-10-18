from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.recipes.models import (
    Recipe,
    RecipeProductInput,
    RecipeSelectedSupplyInput,
    RecipeStep,
    RecipeStepDependency,
    RecipeStepResource,
    RecipeSupplyInput,
)


class RecipeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, recipe_id: UUID, *, lock: bool = False) -> Recipe | None:
        statement = select(Recipe).where(Recipe.id == recipe_id)
        if lock:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return self.session.scalar(statement)

    def base_for_product(self, product_id: UUID) -> Recipe | None:
        return self.session.scalar(
            select(Recipe).where(
                Recipe.product_id == product_id, Recipe.product_variant_id.is_(None)
            )
        )

    def list_for_variant(self, variant_id: UUID) -> list[Recipe]:
        return list(
            self.session.scalars(
                select(Recipe)
                .where(Recipe.product_variant_id == variant_id)
                .order_by(Recipe.name, Recipe.id)
            )
        )

    def steps(self, recipe_id: UUID) -> list[RecipeStep]:
        return list(
            self.session.scalars(
                select(RecipeStep)
                .where(RecipeStep.recipe_id == recipe_id)
                .order_by(RecipeStep.position, RecipeStep.id)
            )
        )

    def dependencies(self, recipe_id: UUID) -> list[RecipeStepDependency]:
        return list(
            self.session.scalars(
                select(RecipeStepDependency).where(
                    RecipeStepDependency.recipe_id == recipe_id
                )
            )
        )

    def supply_inputs(self, recipe_id: UUID) -> list[RecipeSupplyInput]:
        return list(
            self.session.scalars(
                select(RecipeSupplyInput)
                .join(RecipeStep, RecipeSupplyInput.step_id == RecipeStep.id)
                .where(RecipeStep.recipe_id == recipe_id)
            )
        )

    def selected_supply_inputs(
        self, recipe_id: UUID
    ) -> list[RecipeSelectedSupplyInput]:
        return list(
            self.session.scalars(
                select(RecipeSelectedSupplyInput)
                .join(RecipeStep, RecipeSelectedSupplyInput.step_id == RecipeStep.id)
                .where(RecipeStep.recipe_id == recipe_id)
                .order_by(RecipeSelectedSupplyInput.definition_id)
            )
        )

    def product_inputs(self, recipe_id: UUID) -> list[RecipeProductInput]:
        return list(
            self.session.scalars(
                select(RecipeProductInput)
                .join(RecipeStep, RecipeProductInput.step_id == RecipeStep.id)
                .where(RecipeStep.recipe_id == recipe_id)
            )
        )

    def resources(self, recipe_id: UUID) -> list[RecipeStepResource]:
        return list(
            self.session.scalars(
                select(RecipeStepResource)
                .join(RecipeStep, RecipeStepResource.step_id == RecipeStep.id)
                .where(RecipeStep.recipe_id == recipe_id)
                .order_by(RecipeStepResource.key)
            )
        )

    def clear_steps(self, recipe_id: UUID) -> None:
        step_ids = select(RecipeStep.id).where(RecipeStep.recipe_id == recipe_id)
        self.session.execute(
            delete(RecipeStepResource).where(RecipeStepResource.step_id.in_(step_ids))
        )
        self.session.execute(
            delete(RecipeSelectedSupplyInput).where(
                RecipeSelectedSupplyInput.step_id.in_(step_ids)
            )
        )
        self.session.execute(
            delete(RecipeSupplyInput).where(RecipeSupplyInput.step_id.in_(step_ids))
        )
        self.session.execute(
            delete(RecipeProductInput).where(RecipeProductInput.step_id.in_(step_ids))
        )
        self.session.execute(
            delete(RecipeStepDependency).where(
                RecipeStepDependency.recipe_id == recipe_id
            )
        )
        self.session.execute(
            delete(RecipeStep).where(RecipeStep.recipe_id == recipe_id)
        )
