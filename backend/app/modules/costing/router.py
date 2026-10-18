from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.db.session import get_db_session
from app.modules.costing.exceptions import CostCalculationNotFoundError
from app.modules.costing.schemas import CostCalculationRead, CostCalculationRequest
from app.modules.costing.service import CostCalculationService
from app.modules.machines.exceptions import MachineNotFoundError
from app.modules.supplies.exceptions import SupplyNotFoundError, UnitConversionError

router = APIRouter(prefix="/cost-calculations", tags=["costing"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]


@router.post(
    "",
    response_model=CostCalculationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Calcular costo técnico",
    description="Resuelve fuentes, calcula y persiste un snapshot inmutable.",
    responses={404: {"description": "Insumo o máquina inexistente"}},
)
def create_cost_calculation(
    payload: CostCalculationRequest, session: DatabaseSession
) -> CostCalculationRead:
    try:
        return CostCalculationService(session).create(payload)
    except (SupplyNotFoundError, MachineNotFoundError) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
        ) from error
    except UnitConversionError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    except PersistenceError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo guardar el cálculo técnico",
        ) from error


@router.get(
    "/{calculation_id}",
    response_model=CostCalculationRead,
    summary="Consultar costo técnico histórico",
    description="Devuelve el snapshot persistido sin recalcular fuentes actuales.",
    responses={404: {"description": "Cálculo inexistente"}},
)
def get_cost_calculation(
    calculation_id: UUID, session: DatabaseSession
) -> CostCalculationRead:
    try:
        return CostCalculationService(session).get(calculation_id)
    except CostCalculationNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
        ) from error
