from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.recipes.models import RecipeSupplyInput
from app.modules.supplies.models import (
    Supply,
    SupplyPresentation,
    SupplyPurchase,
    SupplyStockMovement,
)
from app.modules.supplies.reservation_models import SupplyReservation
from app.modules.supplies.schemas import SupplyCategory


class SupplyRepository:
    """Persistencia específica del catálogo, sin confirmar transacciones."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, supply: Supply) -> Supply:
        self._session.add(supply)
        self._session.flush()
        return supply

    def get(self, supply_id: UUID, *, for_update: bool = False) -> Supply | None:
        statement = select(Supply).where(Supply.id == supply_id)
        if for_update:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def list(
        self,
        *,
        active: bool | None = None,
        category: SupplyCategory | None = None,
    ) -> list[Supply]:
        statement = select(Supply).order_by(Supply.created_at, Supply.id)
        if active is not None:
            statement = statement.where(Supply.active.is_(active))
        if category is not None:
            statement = statement.where(Supply.category == category.value)
        return list(self._session.scalars(statement))

    def update(self, supply: Supply, changes: dict[str, object]) -> Supply:
        for field_name, value in changes.items():
            setattr(supply, field_name, value)
        self._session.flush()
        return supply

    def has_production_references(self, supply_id: UUID) -> bool:
        recipe = (
            select(RecipeSupplyInput.id)
            .where(RecipeSupplyInput.supply_id == supply_id)
            .exists()
        )
        reservation = (
            select(SupplyReservation.id)
            .where(SupplyReservation.supply_id == supply_id)
            .exists()
        )
        return bool(self._session.scalar(select(recipe | reservation)))

    def has_movements(self, supply_id: UUID) -> bool:
        statement = select(
            select(SupplyStockMovement.id)
            .where(SupplyStockMovement.supply_id == supply_id)
            .exists()
        )
        return bool(self._session.scalar(statement))


class SupplyPresentationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, presentation: SupplyPresentation) -> SupplyPresentation:
        self._session.add(presentation)
        self._session.flush()
        return presentation

    def get(self, presentation_id: UUID) -> SupplyPresentation | None:
        return self._session.get(SupplyPresentation, presentation_id)

    def list(self, supply_id: UUID) -> list[SupplyPresentation]:
        statement = (
            select(SupplyPresentation)
            .where(SupplyPresentation.supply_id == supply_id)
            .order_by(SupplyPresentation.created_at, SupplyPresentation.id)
        )
        return list(self._session.scalars(statement))


class SupplyPurchaseRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, purchase: SupplyPurchase) -> SupplyPurchase:
        self._session.add(purchase)
        self._session.flush()
        return purchase

    def list(self, supply_id: UUID) -> list[SupplyPurchase]:
        statement = (
            select(SupplyPurchase)
            .where(SupplyPurchase.supply_id == supply_id)
            .order_by(
                SupplyPurchase.purchased_at.desc(), SupplyPurchase.created_at.desc()
            )
        )
        return list(self._session.scalars(statement))

    def latest(self, supply_id: UUID) -> SupplyPurchase | None:
        statement = (
            select(SupplyPurchase)
            .where(SupplyPurchase.supply_id == supply_id)
            .order_by(
                SupplyPurchase.purchased_at.desc(), SupplyPurchase.created_at.desc()
            )
            .limit(1)
        )
        return self._session.scalar(statement)


class StockMovementRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, movement: SupplyStockMovement) -> SupplyStockMovement:
        self._session.add(movement)
        self._session.flush()
        return movement

    def stock(self, supply_id: UUID) -> Decimal:
        statement = select(
            func.coalesce(func.sum(SupplyStockMovement.quantity), 0)
        ).where(SupplyStockMovement.supply_id == supply_id)
        value = self._session.scalar(statement)
        return Decimal(value or 0)

    def list(self, supply_id: UUID) -> list[SupplyStockMovement]:
        statement = (
            select(SupplyStockMovement)
            .where(SupplyStockMovement.supply_id == supply_id)
            .order_by(
                SupplyStockMovement.occurred_at.desc(),
                SupplyStockMovement.created_at.desc(),
            )
        )
        return list(self._session.scalars(statement))
