from uuid import UUID

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, aliased

from app.modules.assets.composition import (
    lock_composition,
    store_components,
    validate_composition,
)
from app.modules.assets.exceptions import AssetConflictError
from app.modules.assets.models import Asset, AssetRevision
from app.modules.assets.schemas import RevisionRead
from app.modules.assets.service import AssetService
from app.modules.assets.structure_models import (
    AssetCompatibility,
    AssetCompositionComponent,
    AssetFamily,
)
from app.modules.assets.structure_schemas import (
    CompatibilityPage,
    ComponentRead,
    ComponentUpdateRead,
    CompositionRevisionCreate,
    FamilyCreate,
    FamilyUpdate,
    RelatedAssetRead,
)


class AssetStructureService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.assets = AssetService(session)

    def create_family(self, payload: FamilyCreate) -> AssetFamily:
        with self.assets.transaction():
            family = AssetFamily(**payload.model_dump())
            self.session.add(family)
        return family

    def update_family(self, family_id: UUID, payload: FamilyUpdate) -> AssetFamily:
        with self.assets.transaction():
            family = self.assets.get_family(family_id)
            for key, value in payload.model_dump(exclude_unset=True).items():
                setattr(family, key, value)
        return family

    def families(self, offset: int, limit: int) -> list[AssetFamily]:
        return list(
            self.session.scalars(
                select(AssetFamily)
                .order_by(AssetFamily.name, AssetFamily.id)
                .offset(offset)
                .limit(limit)
            )
        )

    def composition(self, asset_id: UUID, revision_id: UUID) -> list[ComponentRead]:
        self.assets.get_revision(asset_id, revision_id)
        return [
            ComponentRead.model_validate(row)
            for row in self.session.scalars(
                select(AssetCompositionComponent)
                .where(AssetCompositionComponent.parent_revision_id == revision_id)
                .order_by(AssetCompositionComponent.child_asset_id)
            )
        ]

    def publish_composition(
        self, asset_id: UUID, payload: CompositionRevisionCreate
    ) -> RevisionRead:
        with self.assets.transaction():
            lock_composition(self.session)
            asset = self.assets.get_asset(asset_id, lock=True)
            source = self.assets.get_revision(asset_id, payload.base_revision_id)
            if asset.current_revision_id != source.id:
                raise AssetConflictError(
                    "La revisión actual cambió; "
                    "revisar la composición antes de publicar"
                )
            validate_composition(self.session, asset_id, payload.components)
            revision = self.assets.append_revision(
                asset, payload.note if payload.note is not None else source.note
            )
            self.assets.copy_revision_files(source.id, revision.id)
            store_components(self.session, revision.id, payload.components)
            result = RevisionRead.model_validate(revision)
        return result

    def updates(self, asset_id: UUID, revision_id: UUID) -> list[ComponentUpdateRead]:
        self.assets.get_revision(asset_id, revision_id)
        pinned = aliased(AssetRevision)
        current = aliased(AssetRevision)
        rows = self.session.execute(
            select(AssetCompositionComponent, Asset, pinned, current)
            .join(Asset, Asset.id == AssetCompositionComponent.child_asset_id)
            .join(pinned, pinned.id == AssetCompositionComponent.child_revision_id)
            .join(current, current.id == Asset.current_revision_id)
            .where(AssetCompositionComponent.parent_revision_id == revision_id)
            .order_by(Asset.code)
        ).all()
        return [
            ComponentUpdateRead(
                child_asset_id=child.id,
                code=child.code,
                name=child.name,
                archived=child.archived,
                pinned_revision_id=old.id,
                pinned_revision_number=old.number,
                current_revision_id=new.id,
                current_revision_number=new.number,
                update_available=old.id != new.id,
            )
            for _, child, old, new in rows
        ]

    def put_compatibility(self, asset_id: UUID, other_id: UUID) -> RelatedAssetRead:
        if asset_id == other_id:
            raise AssetConflictError(
                "La compatibilidad relaciona dos recursos distintos"
            )
        left, right = sorted((asset_id, other_id))
        with self.assets.transaction():
            self.assets.get_asset(left, lock=True)
            self.assets.get_asset(right, lock=True)
            self.session.execute(
                insert(AssetCompatibility)
                .values(left_asset_id=left, right_asset_id=right)
                .on_conflict_do_nothing()
            )
            result = RelatedAssetRead.model_validate(self.assets.get_asset(other_id))
        return result

    def remove_compatibility(self, asset_id: UUID, other_id: UUID) -> None:
        left, right = sorted((asset_id, other_id))
        with self.assets.transaction():
            self.assets.get_asset(left, lock=True)
            self.assets.get_asset(right, lock=True)
            self.session.execute(
                delete(AssetCompatibility).where(
                    AssetCompatibility.left_asset_id == left,
                    AssetCompatibility.right_asset_id == right,
                )
            )

    def compatibilities(
        self, asset_id: UUID, offset: int, limit: int
    ) -> CompatibilityPage:
        self.assets.get_asset(asset_id)
        query = select(Asset).join(
            AssetCompatibility,
            or_(
                and_(
                    AssetCompatibility.left_asset_id == asset_id,
                    AssetCompatibility.right_asset_id == Asset.id,
                ),
                and_(
                    AssetCompatibility.right_asset_id == asset_id,
                    AssetCompatibility.left_asset_id == Asset.id,
                ),
            ),
        )
        total = (
            self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        )
        rows = self.session.scalars(
            query.order_by(Asset.name, Asset.id).offset(offset).limit(limit)
        )
        return CompatibilityPage(
            items=[RelatedAssetRead.model_validate(row) for row in rows],
            total=total,
            offset=offset,
            limit=limit,
        )
