from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.db.session import get_db_session
from app.modules.projects.exceptions import (
    ProjectNotCancellableError,
    ProjectNotFoundError,
)
from app.modules.projects.models import Project
from app.modules.projects.schemas import ProjectRead
from app.modules.projects.service import ProjectService
from app.modules.projects.types import ProjectStatus

router = APIRouter(prefix="/projects", tags=["projects"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]


@router.get("", response_model=list[ProjectRead], summary="Listar proyectos")
def list_projects(
    session: DatabaseSession,
    project_status: Annotated[ProjectStatus | None, Query(alias="status")] = None,
) -> list[Project]:
    return ProjectService(session).list(project_status)


@router.get(
    "/{project_id}",
    response_model=ProjectRead,
    summary="Consultar proyecto",
    responses={404: {"description": "Proyecto inexistente"}},
)
def get_project(project_id: UUID, session: DatabaseSession) -> Project:
    try:
        return ProjectService(session).get(project_id)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/{project_id}/cancel",
    response_model=ProjectRead,
    summary="Cancelar proyecto pendiente",
    responses={
        404: {"description": "Proyecto inexistente"},
        409: {"description": "Estado inválido"},
    },
)
def cancel_project(project_id: UUID, session: DatabaseSession) -> Project:
    try:
        return ProjectService(session).cancel(project_id)
    except ProjectNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
        ) from error
    except ProjectNotCancellableError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(error)
        ) from error
    except PersistenceError as error:
        raise HTTPException(
            status_code=500, detail="No se pudo cancelar el proyecto"
        ) from error
