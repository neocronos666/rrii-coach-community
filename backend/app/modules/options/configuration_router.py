from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.modules.options.configuration_schemas import (
    ConfigurationResolveInput,
    ProductConfigurationInput,
    ProductConfigurationRead,
    ResolvedConfiguration,
)
from app.modules.options.configuration_service import ProductConfigurationService
from app.modules.options.router import errors
from app.modules.options.schemas import OptionErrorRead

router = APIRouter(
    tags=["options"],
    responses={status: {"model": OptionErrorRead} for status in (404, 409, 500)},
)


def configuration_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> ProductConfigurationService:
    return ProductConfigurationService(session)


Service = Annotated[ProductConfigurationService, Depends(configuration_service)]


@router.get(
    "/products/{product_id}/configuration",
    response_model=ProductConfigurationRead,
    summary="Consultar características y opciones permitidas del producto",
)
def get_configuration(product_id: UUID, service: Service) -> ProductConfigurationRead:
    with errors():
        return service.get(product_id)


@router.put(
    "/products/{product_id}/configuration",
    response_model=ProductConfigurationRead,
    summary="Reemplazar atómicamente la configuración del producto",
    description=(
        "La lista completa declara características, opciones, defaults "
        "y referencias de contexto. Una lista vacía retira la configuración."
    ),
)
def replace_configuration(
    product_id: UUID, payload: ProductConfigurationInput, service: Service
) -> ProductConfigurationRead:
    with errors():
        return service.replace(product_id, payload)


@router.post(
    "/products/{product_id}/configuration/resolve",
    response_model=ResolvedConfiguration,
    summary="Resolver selecciones a recursos y revisiones sin crear presupuesto",
    description=(
        "Omitir una característica aplica sus defaults; una lista "
        "explícita vacía no los aplica. El resultado no se persiste "
        "ni consume stock."
    ),
)
def resolve_configuration(
    product_id: UUID, payload: ConfigurationResolveInput, service: Service
) -> ResolvedConfiguration:
    with errors():
        return service.resolve(product_id, payload)
