from typing import BinaryIO
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.modules.assets.exceptions import AssetConflictError, AssetNotFoundError
from app.modules.assets.file_models import AssetRevisionFile, FileRole, StoredFile
from app.modules.assets.file_schemas import (
    FileDifference,
    RevisionFileRead,
    RevisionFilesDiff,
    validate_filename,
)
from app.modules.assets.service import AssetService
from app.modules.assets.storage import LocalAssetStorage
from app.modules.assets.thumbnails import normalize_thumbnail


class AssetFileService:
    def __init__(self, session: Session, storage: LocalAssetStorage) -> None:
        self.session = session
        self.assets = AssetService(session)
        self.storage = storage

    @staticmethod
    def read(attachment: AssetRevisionFile, blob: StoredFile) -> RevisionFileRead:
        return RevisionFileRead(
            id=attachment.id,
            revision_id=attachment.revision_id,
            stored_file_id=blob.id,
            filename=attachment.filename,
            role=FileRole(attachment.role),
            attached_at=attachment.attached_at,
            sha256=blob.sha256,
            size_bytes=blob.size_bytes,
            detected_mime=blob.detected_mime,
            technical_metadata=blob.technical_metadata,
        )

    def list(self, asset_id: UUID, revision_id: UUID) -> list[RevisionFileRead]:
        self.assets.get_revision(asset_id, revision_id)
        rows = self.session.execute(
            select(AssetRevisionFile, StoredFile)
            .join(StoredFile, StoredFile.id == AssetRevisionFile.stored_file_id)
            .where(AssetRevisionFile.revision_id == revision_id)
            .order_by(AssetRevisionFile.filename)
        ).all()
        return [self.read(attachment, blob) for attachment, blob in rows]

    def attach(
        self,
        asset_id: UUID,
        revision_id: UUID,
        filename: str,
        role: FileRole,
        source: BinaryIO,
    ) -> RevisionFileRead:
        validate_filename(filename)
        if role is FileRole.THUMBNAIL:
            source = normalize_thumbnail(source, self.storage.max_bytes)
        # El trabajo de disco comienza antes de tomar locks de dominio.
        with self.storage.stage(source) as staged, self.assets.transaction():
            self.assets.get_asset(asset_id, lock=True)
            self.assets.get_revision(asset_id, revision_id)
            if role is FileRole.THUMBNAIL:
                current = self.session.execute(
                    select(AssetRevisionFile, StoredFile)
                    .join(StoredFile, StoredFile.id == AssetRevisionFile.stored_file_id)
                    .where(
                        AssetRevisionFile.revision_id == revision_id,
                        AssetRevisionFile.role == FileRole.THUMBNAIL.value,
                    )
                ).one_or_none()
                if current is not None:
                    attachment, blob = current
                    if attachment.filename == filename and blob.sha256 == staged.sha256:
                        # Reintento semántico: mismo nombre y PNG normalizado.
                        with self.storage.open_verified(blob.sha256, blob.size_bytes):
                            pass
                        return self.read(attachment, blob)
                    raise AssetConflictError(
                        "La revisión ya tiene miniatura; "
                        "crear otra revisión para cambiarla"
                    )
            existing = self.session.scalar(
                select(AssetRevisionFile.id).where(
                    AssetRevisionFile.revision_id == revision_id,
                    AssetRevisionFile.filename == filename,
                )
            )
            if existing is not None:
                raise AssetConflictError(
                    "El nombre ya está adjunto a esta revisión; "
                    "crear otra revisión para reemplazarlo"
                )
            # Un lock por hash serializa publicación + registro entre distintos Assets.
            # Colisiones del lock sólo serializan trabajo.
            # La identidad usa SHA-256 completo.
            lock_key = int.from_bytes(bytes.fromhex(staged.sha256)[:8], signed=True)
            self.session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key}
            )
            blob = self.session.scalar(
                select(StoredFile).where(StoredFile.sha256 == staged.sha256)
            )
            if blob is not None and blob.size_bytes != staged.size_bytes:
                raise AssetConflictError("El hash registrado tiene un tamaño diferente")
            self.storage.publish(staged)
            if blob is None:
                blob = StoredFile(
                    sha256=staged.sha256,
                    size_bytes=staged.size_bytes,
                    detected_mime=staged.detected_mime,
                    storage_key=staged.storage_key,
                    technical_metadata=staged.technical_metadata,
                )
                self.session.add(blob)
                self.session.flush()
            attachment = AssetRevisionFile(
                revision_id=revision_id,
                stored_file_id=blob.id,
                filename=filename,
                role=role.value,
            )
            self.session.add(attachment)
            self.session.flush()
            result = self.read(attachment, blob)
        return result

    def download(
        self, asset_id: UUID, revision_id: UUID, attachment_id: UUID
    ) -> tuple[RevisionFileRead, BinaryIO]:
        self.assets.get_revision(asset_id, revision_id)
        row = self.session.execute(
            select(AssetRevisionFile, StoredFile)
            .join(StoredFile, StoredFile.id == AssetRevisionFile.stored_file_id)
            .where(
                AssetRevisionFile.revision_id == revision_id,
                AssetRevisionFile.id == attachment_id,
            )
        ).one_or_none()
        if row is None:
            raise AssetNotFoundError("No existe el archivo en esta revisión")
        attachment, blob = row
        return self.read(attachment, blob), self.storage.open_verified(
            blob.sha256, blob.size_bytes
        )

    def compare(
        self, asset_id: UUID, from_revision_id: UUID, to_revision_id: UUID
    ) -> RevisionFilesDiff:
        before = {row.filename: row for row in self.list(asset_id, from_revision_id)}
        after = {row.filename: row for row in self.list(asset_id, to_revision_id)}
        result = RevisionFilesDiff(
            from_revision_id=from_revision_id,
            to_revision_id=to_revision_id,
            added=[],
            removed=[],
            content_changed=[],
            role_changed=[],
            unchanged=[],
        )
        for filename in sorted(before.keys() | after.keys()):
            left, right = before.get(filename), after.get(filename)
            difference = FileDifference(filename=filename, before=left, after=right)
            if left is None:
                result.added.append(difference)
            elif right is None:
                result.removed.append(difference)
            else:
                if left.sha256 != right.sha256:
                    result.content_changed.append(difference)
                if left.role != right.role:
                    result.role_changed.append(difference)
                if left.sha256 == right.sha256 and left.role == right.role:
                    result.unchanged.append(filename)
        return result

    def thumbnail(
        self, asset_id: UUID, revision_id: UUID
    ) -> tuple[RevisionFileRead, BinaryIO]:
        self.assets.get_revision(asset_id, revision_id)
        attachment_id = self.session.scalar(
            select(AssetRevisionFile.id).where(
                AssetRevisionFile.revision_id == revision_id,
                AssetRevisionFile.role == FileRole.THUMBNAIL.value,
            )
        )
        if attachment_id is None:
            raise AssetNotFoundError("La revisión no tiene miniatura")
        return self.download(asset_id, revision_id, attachment_id)
