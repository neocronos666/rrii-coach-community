from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.modules.recipes.action_templates import render_action
from app.modules.recipes.service_models import ServiceDefinition
from app.modules.recipes.service_schemas import (
    ServiceActionPreview,
    ServiceActionPreviewInput,
    ServiceDefinitionCreate,
    ServiceDefinitionUpdate,
)


class ServiceDefinitionNotFoundError(Exception):
    pass


class ServiceDefinitionConflictError(Exception):
    pass


class ServiceCatalog:
    def __init__(self, session: Session) -> None:
        self.session = session

    @contextmanager
    def transaction(self) -> Iterator[None]:
        try:
            yield
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            raise ServiceDefinitionConflictError(
                "El servicio entra en conflicto con datos existentes"
            ) from error
        except SQLAlchemyError as error:
            self.session.rollback()
            raise PersistenceError("No se pudo guardar el servicio") from error
        except Exception:
            self.session.rollback()
            raise

    def get(self, definition_id: UUID, *, lock: bool = False) -> ServiceDefinition:
        query = select(ServiceDefinition).where(ServiceDefinition.id == definition_id)
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        definition = self.session.scalar(query)
        if definition is None:
            raise ServiceDefinitionNotFoundError("No existe el servicio")
        return definition

    def create(self, payload: ServiceDefinitionCreate) -> ServiceDefinition:
        with self.transaction():
            definition = ServiceDefinition(**payload.model_dump())
            self.session.add(definition)
        return definition

    def update(
        self, definition_id: UUID, payload: ServiceDefinitionUpdate
    ) -> ServiceDefinition:
        with self.transaction():
            definition = self.get(definition_id, lock=True)
            for key, value in payload.model_dump(exclude_unset=True).items():
                setattr(definition, key, value)
        return definition

    def list(
        self, active: bool | None, search: str | None, offset: int, limit: int
    ) -> list[ServiceDefinition]:
        query = select(ServiceDefinition)
        if active is not None:
            query = query.where(ServiceDefinition.active == active)
        if search:
            query = query.where(
                ServiceDefinition.name.icontains(search, autoescape=True)
            )
        return list(
            self.session.scalars(
                query.order_by(ServiceDefinition.name, ServiceDefinition.id)
                .offset(offset)
                .limit(limit)
            )
        )

    def preview(
        self, definition_id: UUID, payload: ServiceActionPreviewInput
    ) -> ServiceActionPreview:
        definition = self.get(definition_id)
        values: dict[str, str] = {key: value for key, value in payload.values.items()}
        action = (
            render_action(definition.action_template, values)
            if definition.action_template is not None
            else definition.name
        )
        return ServiceActionPreview(
            service_definition_id=definition.id,
            action=action,
            instructions=definition.instructions,
        )
