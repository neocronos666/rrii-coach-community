from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.modules.options.exceptions import OptionConflictError, OptionNotFoundError
from app.modules.production.plan_schemas import (
    PlanPreviewCreate,
    ProductionPlanCreate,
    ProductionPlanRead,
    ProductionPreview,
)
from app.modules.production.plan_service import ProductionPlanService
from app.modules.products.stock_router import DatabaseSession
from app.modules.products.stock_router import errors as stock_errors
from app.modules.recipes.exceptions import InvalidRecipeError, RecipeNotFoundError

router = APIRouter(tags=["production-plans"])


@contextmanager
def errors() -> Iterator[None]:
    with stock_errors():
        try:
            yield
        except (RecipeNotFoundError, OptionNotFoundError) as error:
            raise HTTPException(404, str(error)) from error
        except (InvalidRecipeError, OptionConflictError) as error:
            raise HTTPException(409, str(error)) from error


@router.post(
    "/recipes/{recipe_id}/production-preview", response_model=ProductionPreview
)
def preview(
    recipe_id: UUID, payload: PlanPreviewCreate, session: DatabaseSession
) -> ProductionPreview:
    with errors():
        return ProductionPlanService(session).preview(
            recipe_id, payload.target_quantity, payload.variant_id, payload.selections
        )


@router.post(
    "/orders/{order_id}/production-plans",
    response_model=ProductionPlanRead,
    status_code=201,
)
def create_for_order(
    order_id: UUID, payload: ProductionPlanCreate, session: DatabaseSession
) -> ProductionPlanRead:
    with errors():
        service = ProductionPlanService(session)
        return service.read(service.create(payload, order_id=order_id))


@router.post(
    "/project-components/{component_id}/production-plans",
    response_model=ProductionPlanRead,
    status_code=201,
)
def create_for_component(
    component_id: UUID, payload: ProductionPlanCreate, session: DatabaseSession
) -> ProductionPlanRead:
    with errors():
        service = ProductionPlanService(session)
        return service.read(service.create(payload, component_id=component_id))


@router.get("/production-plans/{plan_id}", response_model=ProductionPlanRead)
def get_plan(plan_id: UUID, session: DatabaseSession) -> ProductionPlanRead:
    with errors():
        service = ProductionPlanService(session)
        return service.read(service.get(plan_id))
