from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.db.session import get_db_session
from app.modules.assets.exceptions import AssetConflictError, AssetNotFoundError
from app.modules.assets.schemas import (
    AssetCreate,
    AssetRead,
    AssetUpdate,
    CategoryCreate,
    CategoryRead,
    RevisionCreate,
    RevisionRead,
)
from app.modules.assets.service import AssetService
from app.modules.assets.storage import EmptyFileError, StorageError, UploadTooLargeError
from app.modules.assets.thumbnails import InvalidThumbnailError

router = APIRouter(tags=["assets"])


def asset_service(session: Annotated[Session, Depends(get_db_session)]) -> AssetService:
    return AssetService(session)


Service = Annotated[AssetService, Depends(asset_service)]
Offset = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=100)]


@contextmanager
def errors() -> Iterator[None]:
    try:
        yield
    except AssetNotFoundError as error:
        raise HTTPException(404, str(error)) from error
    except AssetConflictError as error:
        raise HTTPException(409, str(error)) from error
    except InvalidThumbnailError as error:
        raise HTTPException(422, str(error)) from error
    except EmptyFileError as error:
        raise HTTPException(422, "El archivo no puede estar vacío") from error
    except UploadTooLargeError as error:
        raise HTTPException(413, "El archivo supera el límite de carga") from error
    except (StorageError, OSError) as error:
        raise HTTPException(
            503, "Almacenamiento de recursos no disponible o contenido inconsistente"
        ) from error
    except PersistenceError as error:
        raise HTTPException(500, "No se pudo guardar la biblioteca") from error


@router.get(
    "/asset-categories",
    response_model=list[CategoryRead],
    summary="Listar categorías de recursos",
)
def list_categories(
    service: Service, offset: Offset = 0, limit: Limit = 50
) -> list[CategoryRead]:
    return [
        CategoryRead.model_validate(row)
        for row in service.repository.categories(offset, limit)
    ]


@router.post(
    "/asset-categories",
    response_model=CategoryRead,
    status_code=201,
    summary="Crear categoría de recursos",
)
def create_category(payload: CategoryCreate, service: Service) -> CategoryRead:
    with errors():
        return CategoryRead.model_validate(service.create_category(payload))


@router.patch(
    "/asset-categories/{category_id}",
    response_model=CategoryRead,
    summary="Renombrar categoría de recursos",
)
def rename_category(
    category_id: UUID, payload: CategoryCreate, service: Service
) -> CategoryRead:
    with errors():
        return CategoryRead.model_validate(
            service.rename_category(category_id, payload)
        )


@router.delete(
    "/asset-categories/{category_id}",
    status_code=204,
    summary="Eliminar categoría y reasignar recursos a Uncategorized",
)
def delete_category(category_id: UUID, service: Service) -> Response:
    with errors():
        service.delete_category(category_id)
        return Response(status_code=204)


@router.post(
    "/assets",
    response_model=AssetRead,
    status_code=201,
    summary="Registrar recurso con su primera revisión",
)
def create_asset(payload: AssetCreate, service: Service) -> AssetRead:
    with errors():
        return AssetRead.model_validate(service.create(payload))


@router.get(
    "/assets", response_model=list[AssetRead], summary="Listar recursos registrados"
)
def list_assets(
    service: Service,
    archived: bool | None = False,
    search: Annotated[str | None, Query(max_length=255)] = None,
    category_id: UUID | None = None,
    family_id: UUID | None = None,
    offset: Offset = 0,
    limit: Limit = 50,
) -> list[AssetRead]:
    return [
        AssetRead.model_validate(row)
        for row in service.repository.assets(
            archived, search, category_id, offset, limit, family_id
        )
    ]


@router.get("/assets/{asset_id}", response_model=AssetRead, summary="Obtener recurso")
def get_asset(asset_id: UUID, service: Service) -> AssetRead:
    with errors():
        return AssetRead.model_validate(service.get_asset(asset_id))


@router.patch(
    "/assets/{asset_id}",
    response_model=AssetRead,
    summary="Actualizar metadata o archivado del recurso",
)
def update_asset(asset_id: UUID, payload: AssetUpdate, service: Service) -> AssetRead:
    with errors():
        return AssetRead.model_validate(service.update(asset_id, payload))


@router.delete(
    "/assets/{asset_id}",
    response_model=AssetRead,
    summary="Archivar recurso sin eliminar historia",
)
def archive_asset(asset_id: UUID, service: Service) -> AssetRead:
    with errors():
        return AssetRead.model_validate(service.archive(asset_id))


@router.post(
    "/assets/{asset_id}/revisions",
    response_model=RevisionRead,
    status_code=201,
    summary="Crear revisión explícita y establecerla como actual",
)
def create_revision(
    asset_id: UUID, payload: RevisionCreate, service: Service
) -> RevisionRead:
    with errors():
        return RevisionRead.model_validate(service.create_revision(asset_id, payload))


@router.get(
    "/assets/{asset_id}/revisions",
    response_model=list[RevisionRead],
    summary="Listar revisiones del recurso",
)
def list_revisions(
    asset_id: UUID, service: Service, offset: Offset = 0, limit: Limit = 50
) -> list[RevisionRead]:
    with errors():
        service.get_asset(asset_id)
        return [
            RevisionRead.model_validate(row)
            for row in service.repository.revisions(asset_id, offset, limit)
        ]


@router.get(
    "/assets/{asset_id}/revisions/{revision_id}",
    response_model=RevisionRead,
    summary="Obtener revisión del recurso",
)
def get_revision(asset_id: UUID, revision_id: UUID, service: Service) -> RevisionRead:
    with errors():
        return RevisionRead.model_validate(service.get_revision(asset_id, revision_id))


@router.post(
    "/assets/{asset_id}/revisions/{revision_id}/restore",
    response_model=RevisionRead,
    status_code=201,
    summary="Restaurar creando una revisión nueva sin reescribir historia",
)
def restore_revision(
    asset_id: UUID, revision_id: UUID, payload: RevisionCreate, service: Service
) -> RevisionRead:
    with errors():
        return RevisionRead.model_validate(
            service.create_revision(asset_id, payload, revision_id)
        )
