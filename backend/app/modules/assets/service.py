from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.modules.assets.composition import (
    components,
    lock_composition,
    store_components,
    validate_composition,
)
from app.modules.assets.exceptions import AssetConflictError, AssetNotFoundError
from app.modules.assets.file_models import AssetRevisionFile
from app.modules.assets.models import (
    UNCATEGORIZED_ID,
    Asset,
    AssetCategory,
    AssetRevision,
)
from app.modules.assets.repository import AssetRepository
from app.modules.assets.schemas import (
    AssetCreate,
    AssetUpdate,
    CategoryCreate,
    RevisionCreate,
)
from app.modules.assets.structure_models import AssetFamily


class AssetService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = AssetRepository(session)

    @contextmanager
    def transaction(self) -> Iterator[None]:
        try:
            yield
            self.session.commit()
        except (AssetConflictError, AssetNotFoundError):
            self.session.rollback()
            raise
        except IntegrityError as error:
            self.session.rollback()
            raise AssetConflictError(
                "El recurso entra en conflicto con datos existentes"
            ) from error
        except SQLAlchemyError as error:
            self.session.rollback()
            raise PersistenceError("No se pudo guardar la biblioteca") from error
        except Exception:
            self.session.rollback()
            raise

    def get_asset(self, asset_id: UUID, *, lock: bool = False) -> Asset:
        asset = self.repository.asset(asset_id, lock=lock)
        if asset is None:
            raise AssetNotFoundError("No existe el recurso")
        return asset

    def get_category(self, category_id: UUID, *, lock: bool = False) -> AssetCategory:
        category = self.repository.category(category_id, lock=lock)
        if category is None:
            raise AssetNotFoundError("No existe la categoría")
        return category

    def get_revision(self, asset_id: UUID, revision_id: UUID) -> AssetRevision:
        revision = self.repository.revision(asset_id, revision_id)
        if revision is None:
            raise AssetNotFoundError("No existe la revisión del recurso")
        return revision

    def get_family(self, family_id: UUID) -> AssetFamily:
        family = self.session.get(AssetFamily, family_id)
        if family is None:
            raise AssetNotFoundError("No existe la familia de diseño")
        return family

    def create_category(self, payload: CategoryCreate) -> AssetCategory:
        with self.transaction():
            category = AssetCategory(name=payload.name)
            self.repository.add(category)
        return category

    def rename_category(
        self, category_id: UUID, payload: CategoryCreate
    ) -> AssetCategory:
        with self.transaction():
            category = self.get_category(category_id, lock=True)
            if category.system_key is not None:
                raise AssetConflictError("La categoría de respaldo está protegida")
            category.name = payload.name
        return category

    def delete_category(self, category_id: UUID) -> None:
        with self.transaction():
            category = self.get_category(category_id, lock=True)
            if category.system_key is not None:
                raise AssetConflictError("La categoría de respaldo está protegida")
            self.session.execute(
                update(Asset)
                .where(Asset.category_id == category_id)
                .values(category_id=UNCATEGORIZED_ID)
            )
            self.session.delete(category)

    def create(self, payload: AssetCreate) -> Asset:
        with self.transaction():
            if payload.family_id is not None:
                self.get_family(payload.family_id)
            category_id = payload.category_id or UNCATEGORIZED_ID
            self.get_category(category_id, lock=True)
            asset = Asset(
                **payload.model_dump(exclude={"category_id", "revision_note"}),
                category_id=category_id,
            )
            self.repository.add(asset)
            revision = AssetRevision(
                asset_id=asset.id, number=1, note=payload.revision_note
            )
            self.repository.add(revision)
            asset.current_revision_id = revision.id
        return asset

    def update(self, asset_id: UUID, payload: AssetUpdate) -> Asset:
        with self.transaction():
            if payload.family_id is not None:
                self.get_family(payload.family_id)
            # Mismo orden que borrado de categoría: categoría antes de recurso.
            if payload.category_id is not None:
                self.get_category(payload.category_id, lock=True)
            asset = self.get_asset(asset_id, lock=True)
            for field, value in payload.model_dump(exclude_unset=True).items():
                setattr(asset, field, value)
        return asset

    def archive(self, asset_id: UUID) -> Asset:
        return self.update(asset_id, AssetUpdate(archived=True))

    def append_revision(
        self, asset: Asset, note: str | None, restored_from: UUID | None = None
    ) -> AssetRevision:
        """Requiere transacción y locks de composición/recurso tomados por el caller."""
        number = (
            self.session.scalar(
                select(func.max(AssetRevision.number)).where(
                    AssetRevision.asset_id == asset.id
                )
            )
            or 0
        ) + 1
        revision = AssetRevision(
            asset_id=asset.id,
            number=number,
            note=note,
            restored_from_revision_id=restored_from,
        )
        self.repository.add(revision)
        asset.current_revision_id = revision.id
        return revision

    def copy_revision_files(self, source_id: UUID, target_id: UUID) -> None:
        for attachment in self.session.scalars(
            select(AssetRevisionFile).where(AssetRevisionFile.revision_id == source_id)
        ).all():
            self.session.add(
                AssetRevisionFile(
                    revision_id=target_id,
                    stored_file_id=attachment.stored_file_id,
                    filename=attachment.filename,
                    role=attachment.role,
                )
            )

    def create_revision(
        self, asset_id: UUID, payload: RevisionCreate, restored_from: UUID | None = None
    ) -> AssetRevision:
        with self.transaction():
            lock_composition(self.session)
            asset = self.get_asset(asset_id, lock=True)
            source_id = restored_from or asset.current_revision_id
            if source_id is None:
                raise AssetConflictError("El recurso no tiene revisión actual")
            source = self.get_revision(asset_id, source_id)
            entries = components(self.session, source_id)
            validate_composition(self.session, asset_id, entries)
            note = (
                source.note if restored_from and payload.note is None else payload.note
            )
            revision = self.append_revision(asset, note, restored_from)
            store_components(self.session, revision.id, entries)
            if restored_from is not None:
                self.copy_revision_files(source_id, revision.id)
        return revision
