from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.modules.costing.preview_schemas import PricingPreviewCreate, PricingPreviewRead
from app.modules.costing.preview_service import PricingPreviewService
from app.modules.machines.exceptions import MachineNotFoundError
from app.modules.recipes.router import errors
from app.modules.supplies.exceptions import SupplyNotFoundError

router = APIRouter(tags=["costing"])


@router.post(
    "/pricing-preview",
    response_model=PricingPreviewRead,
    summary="Simular costo y precio de una receta sin persistir",
)
def pricing_preview(
    payload: PricingPreviewCreate, session: Annotated[Session, Depends(get_db_session)]
) -> PricingPreviewRead:
    with errors():
        try:
            return PricingPreviewService(session).preview(payload)
        except (SupplyNotFoundError, MachineNotFoundError) as error:
            raise HTTPException(404, str(error)) from error
