from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.db.session import get_db_session
from app.modules.machines.exceptions import (
    CommunityMachineLimitError,
    MachineNotFoundError,
)
from app.modules.machines.schemas import (
    MachineCreate,
    MachineRead,
    MachineType,
    MachineUpdate,
)
from app.modules.machines.service import MachineService

router = APIRouter(prefix="/machines", tags=["machines"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]


def machine_service(session: DatabaseSession) -> MachineService:
    return MachineService(session)


MachineServiceDependency = Annotated[MachineService, Depends(machine_service)]


@router.get(
    "",
    response_model=list[MachineRead],
    summary="Listar máquinas",
    description="Lista las máquinas Community con filtros simples opcionales.",
)
def list_machines(
    service: MachineServiceDependency,
    active: Annotated[bool | None, Query()] = None,
    machine_type: Annotated[MachineType | None, Query()] = None,
) -> list[MachineRead]:
    machines = service.list(active=active, machine_type=machine_type)
    return [MachineRead.model_validate(machine) for machine in machines]


@router.post(
    "",
    response_model=MachineRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar máquina",
    description="Registra una máquina y aplica el límite Community en backend.",
    responses={409: {"description": "Límite de máquinas activas alcanzado"}},
)
def create_machine(
    payload: MachineCreate,
    service: MachineServiceDependency,
) -> MachineRead:
    try:
        return MachineRead.model_validate(service.create(payload))
    except CommunityMachineLimitError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except PersistenceError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo guardar la máquina",
        ) from error


@router.get(
    "/{machine_id}",
    response_model=MachineRead,
    summary="Obtener máquina",
    responses={404: {"description": "Máquina inexistente"}},
)
def get_machine(
    machine_id: UUID,
    service: MachineServiceDependency,
) -> MachineRead:
    try:
        return MachineRead.model_validate(service.get(machine_id))
    except MachineNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error


@router.patch(
    "/{machine_id}",
    response_model=MachineRead,
    summary="Actualizar máquina",
    description="Actualiza campos presentes y revalida el límite al reactivar.",
    responses={
        404: {"description": "Máquina inexistente"},
        409: {"description": "Límite de máquinas activas alcanzado"},
    },
)
def update_machine(
    machine_id: UUID,
    payload: MachineUpdate,
    service: MachineServiceDependency,
) -> MachineRead:
    try:
        return MachineRead.model_validate(service.update(machine_id, payload))
    except MachineNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except CommunityMachineLimitError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except PersistenceError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo actualizar la máquina",
        ) from error
