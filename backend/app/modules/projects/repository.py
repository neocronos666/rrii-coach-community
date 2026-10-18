from uuid import UUID

from sqlalchemy import Sequence, select
from sqlalchemy.orm import Session, selectinload

from app.modules.projects.models import Project
from app.modules.projects.types import ProjectStatus

project_code_sequence = Sequence("project_code_sequence")


class ProjectRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def next_code(self, year: int) -> str:
        number = self._session.scalar(project_code_sequence.next_value())
        if number is None:
            raise RuntimeError("No se pudo generar el código de proyecto")
        return f"P-{year}-{number:06d}"

    def add(self, project: Project) -> Project:
        self._session.add(project)
        self._session.flush()
        return project

    def get(self, project_id: UUID) -> Project | None:
        statement = (
            select(Project)
            .options(selectinload(Project.components))
            .where(Project.id == project_id)
        )
        return self._session.scalar(statement)

    def list(self, status: ProjectStatus | None = None) -> list[Project]:
        statement = select(Project).options(selectinload(Project.components))
        if status is not None:
            statement = statement.where(Project.status == status.value)
        statement = statement.order_by(Project.created_at.desc(), Project.id)
        return list(self._session.scalars(statement))
