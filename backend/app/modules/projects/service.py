import logging
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.modules.products.allocation_repository import ProductAllocationRepository
from app.modules.projects.exceptions import (
    ProjectNotCancellableError,
    ProjectNotFoundError,
)
from app.modules.projects.models import Project
from app.modules.projects.repository import ProjectRepository
from app.modules.projects.types import ProjectStatus
from app.modules.supplies.reservation_repository import SupplyReservationRepository

logger = logging.getLogger(__name__)


class ProjectService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._projects = ProjectRepository(session)

    def list(self, status: ProjectStatus | None = None) -> list[Project]:
        return self._projects.list(status)

    def get(self, project_id: UUID) -> Project:
        project = self._projects.get(project_id)
        if project is None:
            raise ProjectNotFoundError("No existe el proyecto solicitado")
        return project

    def cancel(self, project_id: UUID) -> Project:
        try:
            project = self.get(project_id)
            if project.status != ProjectStatus.PENDING.value:
                raise ProjectNotCancellableError(
                    "Solo un proyecto pending puede cancelarse"
                )
            project.status = ProjectStatus.CANCELLED.value
            self._session.flush()
            SupplyReservationRepository(self._session).release_project(project.id)
            ProductAllocationRepository(self._session).release_project(project.id)
            self._session.commit()
            logger.info("project_cancelled project_id=%s", project.id)
            return project
        except (ProjectNotFoundError, ProjectNotCancellableError):
            self._session.rollback()
            raise
        except SQLAlchemyError as error:
            self._session.rollback()
            raise PersistenceError("No se pudo cancelar el proyecto") from error
