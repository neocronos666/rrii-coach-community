from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.assets.models import Asset, AssetCategory, AssetRevision


class AssetRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def asset(self, asset_id: UUID, *, lock: bool = False) -> Asset | None:
        query = select(Asset).where(Asset.id == asset_id)
        return self.session.scalar(
            query.with_for_update().execution_options(populate_existing=True)
            if lock
            else query
        )

    def category(
        self, category_id: UUID, *, lock: bool = False
    ) -> AssetCategory | None:
        query = select(AssetCategory).where(AssetCategory.id == category_id)
        return self.session.scalar(
            query.with_for_update().execution_options(populate_existing=True)
            if lock
            else query
        )

    def revision(self, asset_id: UUID, revision_id: UUID) -> AssetRevision | None:
        return self.session.scalar(
            select(AssetRevision).where(
                AssetRevision.asset_id == asset_id, AssetRevision.id == revision_id
            )
        )

    def revisions(self, asset_id: UUID, offset: int, limit: int) -> list[AssetRevision]:
        return list(
            self.session.scalars(
                select(AssetRevision)
                .where(AssetRevision.asset_id == asset_id)
                .order_by(AssetRevision.number.desc())
                .offset(offset)
                .limit(limit)
            )
        )

    def assets(
        self,
        archived: bool | None,
        search: str | None,
        category_id: UUID | None,
        offset: int,
        limit: int,
        family_id: UUID | None = None,
    ) -> list[Asset]:
        query = select(Asset)
        if archived is not None:
            query = query.where(Asset.archived == archived)
        if search:
            query = query.where(
                Asset.name.icontains(search, autoescape=True)
                | Asset.code.icontains(search, autoescape=True)
            )
        if family_id is not None:
            query = query.where(Asset.family_id == family_id)
        if category_id is not None:
            query = query.where(Asset.category_id == category_id)
        return list(
            self.session.scalars(
                query.order_by(Asset.name, Asset.id).offset(offset).limit(limit)
            )
        )

    def categories(self, offset: int, limit: int) -> list[AssetCategory]:
        return list(
            self.session.scalars(
                select(AssetCategory)
                .order_by(AssetCategory.name, AssetCategory.id)
                .offset(offset)
                .limit(limit)
            )
        )

    def add(self, entity: Asset | AssetCategory | AssetRevision) -> None:
        self.session.add(entity)
        self.session.flush()
