import tempfile
from collections.abc import Iterator
from typing import Annotated, BinaryIO
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.db.session import get_db_session
from app.modules.assets.file_models import FileRole
from app.modules.assets.file_schemas import (
    FileErrorRead,
    Filename,
    RevisionFileRead,
    RevisionFilesDiff,
)
from app.modules.assets.file_service import AssetFileService
from app.modules.assets.router import errors
from app.modules.assets.storage import CHUNK_SIZE, LocalAssetStorage
from app.modules.assets.thumbnails import THUMBNAIL_MAX_BYTES

router = APIRouter(
    prefix="/assets/{asset_id}/revisions",
    tags=["assets"],
    responses={
        404: {"model": FileErrorRead},
        500: {"model": FileErrorRead},
        503: {"model": FileErrorRead},
    },
)


def file_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> AssetFileService:
    settings = get_settings()
    return AssetFileService(
        session,
        LocalAssetStorage(settings.asset_storage_path, settings.asset_max_upload_bytes),
    )


Service = Annotated[AssetFileService, Depends(file_service)]


@router.post(
    "/{revision_id}/files",
    response_model=RevisionFileRead,
    status_code=201,
    summary="Adjuntar contenido binario a una revisión existente",
    description=(
        "Envía bytes como application/octet-stream; filename y role son "
        "metadata lógica. No reemplaza archivos existentes. Permite completar "
        "revisiones históricas. El rol thumbnail normaliza PNG/JPEG estático a PNG "
        "de hasta 512x512, con límite de entrada de 10 MiB y 16 millones de píxeles. "
        "Sólo admite una miniatura por revisión; reintento idéntico conserva su ID."
    ),
    responses={
        400: {"model": FileErrorRead},
        409: {"model": FileErrorRead},
        413: {"model": FileErrorRead},
        415: {"model": FileErrorRead},
        422: {"model": FileErrorRead},
    },
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/octet-stream": {
                    "schema": {"type": "string", "format": "binary"}
                }
            },
        }
    },
)
async def upload_file(
    asset_id: UUID,
    revision_id: UUID,
    filename: Annotated[Filename, Query()],
    role: FileRole,
    request: Request,
    service: Service,
) -> RevisionFileRead:
    if (
        request.headers.get("content-type", "").split(";")[0].strip().lower()
        != "application/octet-stream"
    ):
        raise HTTPException(415, "Enviar el archivo como application/octet-stream")
    if request.headers.get("content-encoding", "identity").lower() != "identity":
        raise HTTPException(415, "Enviar bytes sin compresión de transporte")
    limit = service.storage.max_bytes
    if role is FileRole.THUMBNAIL:
        limit = min(limit, THUMBNAIL_MAX_BYTES)
    declared = request.headers.get("content-length")
    if declared is not None:
        try:
            length = int(declared)
        except ValueError as error:
            raise HTTPException(400, "Content-Length inválido") from error
        if length < 0:
            raise HTTPException(400, "Content-Length inválido")
        if length > limit:
            raise HTTPException(413, "El archivo supera el límite de carga")
    # Temporal acotado a disco; no cargar el body completo ni confiar en Content-Length.
    with errors(), tempfile.TemporaryFile() as temporary:
        size = 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > limit:
                raise HTTPException(413, "El archivo supera el límite de carga")
            await run_in_threadpool(temporary.write, chunk)
        temporary.seek(0)
        return await run_in_threadpool(
            service.attach, asset_id, revision_id, filename, role, temporary
        )


@router.get(
    "/{revision_id}/files",
    response_model=list[RevisionFileRead],
    summary="Listar archivos adjuntos de una revisión",
)
def list_files(
    asset_id: UUID, revision_id: UUID, service: Service
) -> list[RevisionFileRead]:
    with errors():
        return service.list(asset_id, revision_id)


def chunks(content: BinaryIO) -> Iterator[bytes]:
    try:
        while chunk := content.read(CHUNK_SIZE):
            yield chunk
    finally:
        content.close()


@router.get(
    "/{revision_id}/files/{attachment_id}/content",
    summary="Descargar archivo del recurso",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {
                "application/octet-stream": {
                    "schema": {"type": "string", "format": "binary"}
                }
            }
        }
    },
)
def download_file(
    asset_id: UUID, revision_id: UUID, attachment_id: UUID, service: Service
) -> StreamingResponse:
    with errors():
        metadata, content = service.download(asset_id, revision_id, attachment_id)
        return StreamingResponse(
            chunks(content),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": "attachment; filename*=UTF-8''"
                + quote(metadata.filename, safe=""),
                "Content-Length": str(metadata.size_bytes),
                "X-Content-Type-Options": "nosniff",
            },
            background=BackgroundTask(content.close),
        )


@router.get(
    "/{revision_id}/files-diff/{other_revision_id}",
    response_model=RevisionFilesDiff,
    summary="Comparar archivos de dos revisiones por hash y rol",
)
def compare_files(
    asset_id: UUID, revision_id: UUID, other_revision_id: UUID, service: Service
) -> RevisionFilesDiff:
    with errors():
        return service.compare(asset_id, revision_id, other_revision_id)


@router.get(
    "/{revision_id}/thumbnail",
    summary="Ver miniatura PNG normalizada de una revisión",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {"image/png": {"schema": {"type": "string", "format": "binary"}}}
        }
    },
)
def read_thumbnail(
    asset_id: UUID, revision_id: UUID, service: Service
) -> StreamingResponse:
    with errors():
        metadata, content = service.thumbnail(asset_id, revision_id)
        return StreamingResponse(
            chunks(content),
            media_type="image/png",
            headers={
                "Content-Disposition": 'inline; filename="thumbnail.png"',
                "Content-Length": str(metadata.size_bytes),
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "no-cache",
            },
            background=BackgroundTask(content.close),
        )
