from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.db.session import get_db_session
from app.modules.supplies.exceptions import (
    BaseUnitLockedError,
    DuplicateSupplySkuError,
    EstimatedCostUnavailableError,
    InsufficientStockError,
    PresentationNotFoundError,
    SupplyNotFoundError,
    UnitConversionError,
)
from app.modules.supplies.schemas import (
    AdjustmentCreate,
    EstimatedCostRead,
    MovementRead,
    PresentationCreate,
    PresentationRead,
    PurchaseCreate,
    PurchaseRead,
    StockRead,
    SupplyCategory,
    SupplyCreate,
    SupplyRead,
    SupplyUpdate,
)
from app.modules.supplies.service import SupplyService

router = APIRouter(prefix="/supplies", tags=["supplies"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]


def supply_service(session: DatabaseSession) -> SupplyService:
    return SupplyService(session)


SupplyServiceDependency = Annotated[SupplyService, Depends(supply_service)]


def _not_found(error: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))


def _conflict(error: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


def _persistence(error: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="No se pudo completar la operación de persistencia",
    )


@router.get("", response_model=list[SupplyRead], summary="Listar insumos")
def list_supplies(
    service: SupplyServiceDependency,
    active: Annotated[bool | None, Query()] = None,
    category: Annotated[SupplyCategory | None, Query()] = None,
) -> list[SupplyRead]:
    return [
        SupplyRead.model_validate(item)
        for item in service.list_supplies(active=active, category=category)
    ]


@router.post(
    "",
    response_model=SupplyRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar insumo",
    responses={409: {"description": "SKU duplicado"}},
)
def create_supply(
    payload: SupplyCreate, service: SupplyServiceDependency
) -> SupplyRead:
    try:
        return SupplyRead.model_validate(service.create(payload))
    except DuplicateSupplySkuError as error:
        raise _conflict(error) from error
    except PersistenceError as error:
        raise _persistence(error) from error


@router.get(
    "/{supply_id}",
    response_model=SupplyRead,
    summary="Obtener insumo",
    responses={404: {"description": "Insumo inexistente"}},
)
def get_supply(supply_id: UUID, service: SupplyServiceDependency) -> SupplyRead:
    try:
        return SupplyRead.model_validate(service.get(supply_id))
    except SupplyNotFoundError as error:
        raise _not_found(error) from error


@router.patch(
    "/{supply_id}",
    response_model=SupplyRead,
    summary="Actualizar insumo",
    responses={
        404: {"description": "Insumo inexistente"},
        409: {"description": "Conflicto de integridad"},
    },
)
def update_supply(
    supply_id: UUID, payload: SupplyUpdate, service: SupplyServiceDependency
) -> SupplyRead:
    try:
        return SupplyRead.model_validate(service.update(supply_id, payload))
    except SupplyNotFoundError as error:
        raise _not_found(error) from error
    except (BaseUnitLockedError, DuplicateSupplySkuError) as error:
        raise _conflict(error) from error
    except PersistenceError as error:
        raise _persistence(error) from error


@router.get(
    "/{supply_id}/presentations",
    response_model=list[PresentationRead],
    summary="Listar presentaciones",
)
def list_presentations(
    supply_id: UUID, service: SupplyServiceDependency
) -> list[PresentationRead]:
    try:
        return [
            PresentationRead.model_validate(item)
            for item in service.list_presentations(supply_id)
        ]
    except SupplyNotFoundError as error:
        raise _not_found(error) from error


@router.post(
    "/{supply_id}/presentations",
    response_model=PresentationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar presentación",
)
def create_presentation(
    supply_id: UUID, payload: PresentationCreate, service: SupplyServiceDependency
) -> PresentationRead:
    try:
        return PresentationRead.model_validate(
            service.add_presentation(supply_id, payload)
        )
    except SupplyNotFoundError as error:
        raise _not_found(error) from error
    except UnitConversionError as error:
        raise _conflict(error) from error
    except PersistenceError as error:
        raise _persistence(error) from error


@router.post(
    "/{supply_id}/purchases",
    response_model=PurchaseRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar compra",
)
def create_purchase(
    supply_id: UUID, payload: PurchaseCreate, service: SupplyServiceDependency
) -> PurchaseRead:
    try:
        return PurchaseRead.model_validate(service.record_purchase(supply_id, payload))
    except (SupplyNotFoundError, PresentationNotFoundError) as error:
        raise _not_found(error) from error
    except PersistenceError as error:
        raise _persistence(error) from error


@router.get(
    "/{supply_id}/purchases",
    response_model=list[PurchaseRead],
    summary="Listar compras",
)
def list_purchases(
    supply_id: UUID, service: SupplyServiceDependency
) -> list[PurchaseRead]:
    try:
        return [
            PurchaseRead.model_validate(item)
            for item in service.list_purchases(supply_id)
        ]
    except SupplyNotFoundError as error:
        raise _not_found(error) from error


@router.get("/{supply_id}/stock", response_model=StockRead, summary="Consultar stock")
def get_stock(supply_id: UUID, service: SupplyServiceDependency) -> StockRead:
    try:
        return service.stock(supply_id)
    except SupplyNotFoundError as error:
        raise _not_found(error) from error


@router.post(
    "/{supply_id}/adjustments",
    response_model=MovementRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar ajuste",
    responses={409: {"description": "Stock insuficiente"}},
)
def create_adjustment(
    supply_id: UUID, payload: AdjustmentCreate, service: SupplyServiceDependency
) -> MovementRead:
    try:
        return MovementRead.model_validate(service.adjust(supply_id, payload))
    except SupplyNotFoundError as error:
        raise _not_found(error) from error
    except InsufficientStockError as error:
        raise _conflict(error) from error
    except PersistenceError as error:
        raise _persistence(error) from error


@router.get(
    "/{supply_id}/movements",
    response_model=list[MovementRead],
    summary="Listar movimientos",
)
def list_movements(
    supply_id: UUID, service: SupplyServiceDependency
) -> list[MovementRead]:
    try:
        return [
            MovementRead.model_validate(item)
            for item in service.list_movements(supply_id)
        ]
    except SupplyNotFoundError as error:
        raise _not_found(error) from error


@router.get(
    "/{supply_id}/estimated-cost",
    response_model=EstimatedCostRead,
    summary="Consultar costo estimado",
    responses={404: {"description": "Insumo o costo inexistente"}},
)
def get_estimated_cost(
    supply_id: UUID, service: SupplyServiceDependency
) -> EstimatedCostRead:
    try:
        return service.estimated_cost(supply_id)
    except (SupplyNotFoundError, EstimatedCostUnavailableError) as error:
        raise _not_found(error) from error
