from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.modules.assets.file_schemas import FileErrorRead
from app.modules.assets.router import Limit, Offset, errors
from app.modules.assets.schemas import RevisionRead
from app.modules.assets.structure_schemas import (
    CompatibilityPage,
    ComponentRead,
    ComponentUpdateRead,
    CompositionRevisionCreate,
    FamilyCreate,
    FamilyRead,
    FamilyUpdate,
    RelatedAssetRead,
)
from app.modules.assets.structure_service import AssetStructureService

router = APIRouter(
    tags=["assets"],
    responses={
        404: {"model": FileErrorRead},
        409: {"model": FileErrorRead},
        500: {"model": FileErrorRead},
    },
)


def structure_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> AssetStructureService:
    return AssetStructureService(session)


Service = Annotated[AssetStructureService, Depends(structure_service)]


@router.post(
    "/asset-families",
    response_model=FamilyRead,
    status_code=201,
    summary="Crear familia de diseño",
)
def create_family(payload: FamilyCreate, service: Service) -> FamilyRead:
    with errors():
        return FamilyRead.model_validate(service.create_family(payload))


@router.get(
    "/asset-families",
    response_model=list[FamilyRead],
    summary="Listar familias de diseño",
)
def list_families(
    service: Service, offset: Offset = 0, limit: Limit = 50
) -> list[FamilyRead]:
    return [FamilyRead.model_validate(row) for row in service.families(offset, limit)]


@router.get(
    "/asset-families/{family_id}",
    response_model=FamilyRead,
    summary="Consultar familia de diseño",
)
def get_family(family_id: UUID, service: Service) -> FamilyRead:
    with errors():
        return FamilyRead.model_validate(service.assets.get_family(family_id))


@router.patch(
    "/asset-families/{family_id}",
    response_model=FamilyRead,
    summary="Actualizar metadata de familia",
)
def update_family(
    family_id: UUID, payload: FamilyUpdate, service: Service
) -> FamilyRead:
    with errors():
        return FamilyRead.model_validate(service.update_family(family_id, payload))


@router.get(
    "/assets/{asset_id}/revisions/{revision_id}/composition",
    response_model=list[ComponentRead],
    summary="Consultar composición con revisiones fijadas",
)
def get_composition(
    asset_id: UUID, revision_id: UUID, service: Service
) -> list[ComponentRead]:
    with errors():
        return service.composition(asset_id, revision_id)


@router.post(
    "/assets/{asset_id}/composition-revisions",
    response_model=RevisionRead,
    status_code=201,
    summary="Publicar composición o adoptar revisiones hijas explícitamente",
    description=(
        "Exige la revisión base actual y una lista completa de hijos "
        "con revisiones concretas. Crea una revisión del padre y conserva sus "
        "archivos. Una lista vacía retira todos los hijos."
    ),
)
def publish_composition(
    asset_id: UUID, payload: CompositionRevisionCreate, service: Service
) -> RevisionRead:
    with errors():
        return service.publish_composition(asset_id, payload)


@router.get(
    "/assets/{asset_id}/revisions/{revision_id}/component-updates",
    response_model=list[ComponentUpdateRead],
    summary="Consultar actualizaciones disponibles de hijos directos",
)
def component_updates(
    asset_id: UUID, revision_id: UUID, service: Service
) -> list[ComponentUpdateRead]:
    with errors():
        return service.updates(asset_id, revision_id)


@router.get(
    "/assets/{asset_id}/compatibilities",
    response_model=CompatibilityPage,
    summary="Listar compatibilidades positivas; ausencia no implica incompatibilidad",
)
def list_compatibilities(
    asset_id: UUID, service: Service, offset: Offset = 0, limit: Limit = 50
) -> CompatibilityPage:
    with errors():
        return service.compatibilities(asset_id, offset, limit)


@router.put(
    "/assets/{asset_id}/compatibilities/{other_id}",
    response_model=RelatedAssetRead,
    summary="Registrar compatibilidad positiva simétrica",
)
def put_compatibility(
    asset_id: UUID, other_id: UUID, service: Service
) -> RelatedAssetRead:
    with errors():
        return service.put_compatibility(asset_id, other_id)


@router.delete(
    "/assets/{asset_id}/compatibilities/{other_id}",
    status_code=204,
    summary="Retirar compatibilidad explícita sin declarar incompatibilidad",
)
def delete_compatibility(asset_id: UUID, other_id: UUID, service: Service) -> Response:
    with errors():
        service.remove_compatibility(asset_id, other_id)
        return Response(status_code=204)
