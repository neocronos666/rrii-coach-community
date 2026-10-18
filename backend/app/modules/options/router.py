from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.db.session import get_db_session
from app.modules.options.exceptions import OptionConflictError, OptionNotFoundError
from app.modules.options.schemas import (
    OptionDefinitionCreate,
    OptionDefinitionRead,
    OptionDefinitionUpdate,
    OptionErrorRead,
    OptionValueCreate,
    OptionValueRead,
    OptionValueUpdate,
)
from app.modules.options.service import OptionService

router = APIRouter(
    prefix="/option-definitions",
    tags=["options"],
    responses={status: {"model": OptionErrorRead} for status in (404, 409, 500)},
)


def option_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> OptionService:
    return OptionService(session)


Service = Annotated[OptionService, Depends(option_service)]
Offset = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=100)]
Search = Annotated[str | None, Query(max_length=255)]


@contextmanager
def errors() -> Iterator[None]:
    try:
        yield
    except OptionNotFoundError as error:
        raise HTTPException(404, str(error)) from error
    except OptionConflictError as error:
        raise HTTPException(409, str(error)) from error
    except PersistenceError as error:
        raise HTTPException(500, str(error)) from error


@router.post(
    "",
    response_model=OptionDefinitionRead,
    status_code=201,
    summary="Crear característica reutilizable",
)
def create_definition(
    payload: OptionDefinitionCreate, service: Service
) -> OptionDefinitionRead:
    with errors():
        return OptionDefinitionRead.model_validate(service.create_definition(payload))


@router.get(
    "", response_model=list[OptionDefinitionRead], summary="Listar características"
)
def list_definitions(
    service: Service,
    active: bool | None = None,
    search: Search = None,
    offset: Offset = 0,
    limit: Limit = 50,
) -> list[OptionDefinitionRead]:
    with errors():
        return [
            OptionDefinitionRead.model_validate(row)
            for row in service.definitions(active, search, offset, limit)
        ]


@router.get(
    "/{definition_id}",
    response_model=OptionDefinitionRead,
    summary="Consultar característica",
)
def get_definition(definition_id: UUID, service: Service) -> OptionDefinitionRead:
    with errors():
        return OptionDefinitionRead.model_validate(service.definition(definition_id))


@router.patch(
    "/{definition_id}",
    response_model=OptionDefinitionRead,
    summary="Editar o desactivar característica sin borrar sus opciones",
)
def update_definition(
    definition_id: UUID,
    payload: OptionDefinitionUpdate,
    service: Service,
) -> OptionDefinitionRead:
    with errors():
        return OptionDefinitionRead.model_validate(
            service.update_definition(definition_id, payload)
        )


@router.post(
    "/{definition_id}/values",
    response_model=OptionValueRead,
    status_code=201,
    summary="Crear opción semántica con familia de diseño opcional",
)
def create_value(
    definition_id: UUID,
    payload: OptionValueCreate,
    service: Service,
) -> OptionValueRead:
    with errors():
        return OptionValueRead.model_validate(
            service.create_value(definition_id, payload)
        )


@router.get(
    "/{definition_id}/values",
    response_model=list[OptionValueRead],
    summary="Listar opciones de una característica",
)
def list_values(
    definition_id: UUID,
    service: Service,
    active: bool | None = None,
    search: Search = None,
    offset: Offset = 0,
    limit: Limit = 50,
) -> list[OptionValueRead]:
    with errors():
        return [
            OptionValueRead.model_validate(row)
            for row in service.values(definition_id, active, search, offset, limit)
        ]


@router.get(
    "/{definition_id}/values/{value_id}",
    response_model=OptionValueRead,
    summary="Consultar opción dentro de su característica",
)
def get_value(definition_id: UUID, value_id: UUID, service: Service) -> OptionValueRead:
    with errors():
        return OptionValueRead.model_validate(service.value(definition_id, value_id))


@router.patch(
    "/{definition_id}/values/{value_id}",
    response_model=OptionValueRead,
    summary="Editar o desactivar opción sin cambiar su identidad",
)
def update_value(
    definition_id: UUID,
    value_id: UUID,
    payload: OptionValueUpdate,
    service: Service,
) -> OptionValueRead:
    with errors():
        return OptionValueRead.model_validate(
            service.update_value(definition_id, value_id, payload)
        )
