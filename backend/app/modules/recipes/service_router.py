from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.db.session import get_db_session
from app.modules.recipes.action_templates import ActionTemplateError
from app.modules.recipes.service_catalog import (
    ServiceCatalog,
    ServiceDefinitionConflictError,
    ServiceDefinitionNotFoundError,
)
from app.modules.recipes.service_schemas import (
    ServiceActionPreview,
    ServiceActionPreviewInput,
    ServiceDefinitionCreate,
    ServiceDefinitionErrorRead,
    ServiceDefinitionRead,
    ServiceDefinitionUpdate,
)

router = APIRouter(
    prefix="/service-definitions",
    tags=["services"],
    responses={
        status: {"model": ServiceDefinitionErrorRead} for status in (404, 409, 500)
    },
)


def service_catalog(
    session: Annotated[Session, Depends(get_db_session)],
) -> ServiceCatalog:
    return ServiceCatalog(session)


Catalog = Annotated[ServiceCatalog, Depends(service_catalog)]


@contextmanager
def errors() -> Iterator[None]:
    try:
        yield
    except ServiceDefinitionNotFoundError as error:
        raise HTTPException(404, str(error)) from error
    except (ServiceDefinitionConflictError, ActionTemplateError) as error:
        raise HTTPException(409, str(error)) from error
    except PersistenceError as error:
        raise HTTPException(500, str(error)) from error


@router.post(
    "",
    response_model=ServiceDefinitionRead,
    status_code=201,
    summary="Registrar servicio humano reutilizable",
)
def create_service(
    payload: ServiceDefinitionCreate, catalog: Catalog
) -> ServiceDefinitionRead:
    with errors():
        return ServiceDefinitionRead.model_validate(catalog.create(payload))


@router.get("", response_model=list[ServiceDefinitionRead], summary="Listar servicios")
def list_services(
    catalog: Catalog,
    active: bool | None = None,
    search: Annotated[str | None, Query(max_length=255)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[ServiceDefinitionRead]:
    return [
        ServiceDefinitionRead.model_validate(row)
        for row in catalog.list(active, search, offset, limit)
    ]


@router.get(
    "/{definition_id}",
    response_model=ServiceDefinitionRead,
    summary="Consultar servicio",
)
def get_service(definition_id: UUID, catalog: Catalog) -> ServiceDefinitionRead:
    with errors():
        return ServiceDefinitionRead.model_validate(catalog.get(definition_id))


@router.patch(
    "/{definition_id}",
    response_model=ServiceDefinitionRead,
    summary="Editar o desactivar servicio",
)
def update_service(
    definition_id: UUID, payload: ServiceDefinitionUpdate, catalog: Catalog
) -> ServiceDefinitionRead:
    with errors():
        return ServiceDefinitionRead.model_validate(
            catalog.update(definition_id, payload)
        )


@router.post(
    "/{definition_id}/action-preview",
    response_model=ServiceActionPreview,
    summary="Previsualizar frase contextual sin persistirla",
    description=(
        "Los valores son etiquetas de presentación, incluida quantity; "
        "no se usan para cálculos ni consumos."
    ),
)
def preview_action(
    definition_id: UUID, payload: ServiceActionPreviewInput, catalog: Catalog
) -> ServiceActionPreview:
    with errors():
        return catalog.preview(definition_id, payload)
