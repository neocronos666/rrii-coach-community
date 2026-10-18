from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.db.session import get_db_session
from app.modules.options.exceptions import OptionConflictError, OptionNotFoundError
from app.modules.products.exceptions import ProductNotFoundError
from app.modules.recipes.exceptions import InvalidRecipeError, RecipeNotFoundError
from app.modules.recipes.resolution import (
    RecipeResolutionService,
    RecipeResolveInput,
    ResolvedRecipe,
)
from app.modules.recipes.schemas import PlanRead, RecipeCreate, RecipePlan, RecipeRead
from app.modules.recipes.service import RecipeService

router = APIRouter(tags=["recipes"])


def recipe_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> RecipeService:
    return RecipeService(session)


Service = Annotated[RecipeService, Depends(recipe_service)]


@contextmanager
def errors() -> Iterator[None]:
    try:
        yield
    except (RecipeNotFoundError, ProductNotFoundError, OptionNotFoundError) as error:
        raise HTTPException(404, str(error)) from error
    except (InvalidRecipeError, OptionConflictError) as error:
        raise HTTPException(409, str(error)) from error
    except PersistenceError as error:
        raise HTTPException(500, "No se pudo guardar la receta") from error


@router.post(
    "/product-variants/{variant_id}/recipes", response_model=RecipeRead, status_code=201
)
def create_recipe(
    variant_id: UUID, payload: RecipeCreate, service: Service
) -> RecipeRead:
    with errors():
        return RecipeRead.model_validate(service.create(variant_id, payload))


@router.get("/product-variants/{variant_id}/recipes", response_model=list[RecipeRead])
def list_recipes(variant_id: UUID, service: Service) -> list[RecipeRead]:
    with errors():
        service.products.get_variant(variant_id)
        return [
            RecipeRead.model_validate(recipe)
            for recipe in service.repository.list_for_variant(variant_id)
        ]


@router.get("/recipes/{recipe_id}", response_model=RecipeRead)
def get_recipe(recipe_id: UUID, service: Service) -> RecipeRead:
    with errors():
        return RecipeRead.model_validate(service.get(recipe_id))


@router.put("/recipes/{recipe_id}", response_model=RecipeRead)
def update_recipe(
    recipe_id: UUID, payload: RecipeCreate, service: Service
) -> RecipeRead:
    with errors():
        return RecipeRead.model_validate(service.update(recipe_id, payload))


@router.get("/recipes/{recipe_id}/plan", response_model=PlanRead)
def get_plan(recipe_id: UUID, service: Service) -> PlanRead:
    with errors():
        return service.plan(recipe_id)


@router.put("/recipes/{recipe_id}/plan", response_model=PlanRead)
def replace_plan(recipe_id: UUID, payload: RecipePlan, service: Service) -> PlanRead:
    with errors():
        return service.replace_plan(recipe_id, payload)


@router.post(
    "/products/{product_id}/recipe", response_model=RecipeRead, status_code=201
)
def create_base_recipe(
    product_id: UUID, payload: RecipeCreate, service: Service
) -> RecipeRead:
    with errors():
        return RecipeRead.model_validate(service.create_base(product_id, payload))


@router.get("/products/{product_id}/recipe", response_model=RecipeRead)
def get_base_recipe(product_id: UUID, service: Service) -> RecipeRead:
    with errors():
        return RecipeRead.model_validate(service.base(product_id))


@router.post(
    "/products/{product_id}/recipe/resolve",
    response_model=ResolvedRecipe,
    summary="Resolver pasos de receta base según selecciones sin crear producción",
)
def resolve_base_recipe(
    product_id: UUID, payload: RecipeResolveInput, service: Service
) -> ResolvedRecipe:
    with errors():
        return RecipeResolutionService(service.session).resolve(product_id, payload)
