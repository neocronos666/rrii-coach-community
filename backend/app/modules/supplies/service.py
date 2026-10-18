import logging
from uuid import UUID

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.modules.supplies.conversion import UnitConversionService
from app.modules.supplies.exceptions import (
    BaseUnitLockedError,
    DuplicateSupplySkuError,
    EstimatedCostUnavailableError,
    InsufficientStockError,
    PresentationNotFoundError,
    SupplyNotFoundError,
)
from app.modules.supplies.models import (
    Supply,
    SupplyPresentation,
    SupplyPurchase,
    SupplyStockMovement,
)
from app.modules.supplies.repository import (
    StockMovementRepository,
    SupplyPresentationRepository,
    SupplyPurchaseRepository,
    SupplyRepository,
)
from app.modules.supplies.schemas import (
    AdjustmentCreate,
    AdjustmentDirection,
    EstimatedCostRead,
    MovementType,
    PresentationCreate,
    PurchaseCreate,
    StockRead,
    SupplyCategory,
    SupplyCreate,
    SupplyUnit,
    SupplyUpdate,
)

logger = logging.getLogger(__name__)


class SupplyService:
    """Casos de uso transaccionales del catálogo y sus existencias."""

    def __init__(
        self,
        session: Session,
        supplies: SupplyRepository | None = None,
        presentations: SupplyPresentationRepository | None = None,
        purchases: SupplyPurchaseRepository | None = None,
        movements: StockMovementRepository | None = None,
    ) -> None:
        self._session = session
        self._supplies = supplies or SupplyRepository(session)
        self._presentations = presentations or SupplyPresentationRepository(session)
        self._purchases = purchases or SupplyPurchaseRepository(session)
        self._movements = movements or StockMovementRepository(session)

    def list_supplies(
        self,
        *,
        active: bool | None = None,
        category: SupplyCategory | None = None,
    ) -> list[Supply]:
        return self._supplies.list(active=active, category=category)

    def get(self, supply_id: UUID) -> Supply:
        supply = self._supplies.get(supply_id)
        if supply is None:
            raise SupplyNotFoundError("No existe el insumo solicitado")
        return supply

    def create(self, payload: SupplyCreate) -> Supply:
        try:
            data = payload.model_dump(exclude={"category", "base_unit"})
            supply = Supply(
                **data,
                category=payload.category.value,
                base_unit=payload.base_unit.value,
            )
            self._supplies.add(supply)
            self._session.commit()
            logger.info("supply_created supply_id=%s", supply.id)
            return supply
        except IntegrityError as error:
            self._session.rollback()
            if payload.sku is not None:
                raise DuplicateSupplySkuError("El SKU ya está registrado") from error
            raise PersistenceError("No se pudo crear el insumo") from error
        except SQLAlchemyError as error:
            self._rollback("supply_create_failed", error)
            raise PersistenceError("No se pudo crear el insumo") from error

    def update(self, supply_id: UUID, payload: SupplyUpdate) -> Supply:
        try:
            supply = self._lock_supply(supply_id)
            changes = payload.model_dump(exclude_unset=True)
            base_unit = changes.get("base_unit")
            if isinstance(base_unit, SupplyUnit):
                referenced = self._supplies.has_production_references(supply.id)
                if base_unit.value != supply.base_unit and (
                    referenced or self._supplies.has_movements(supply.id)
                ):
                    raise BaseUnitLockedError(
                        "La unidad base está fijada por movimientos, recetas o reservas"
                    )
                changes["base_unit"] = base_unit.value
            category = changes.get("category")
            if isinstance(category, SupplyCategory):
                changes["category"] = category.value
            was_active = supply.active
            self._supplies.update(supply, changes)
            self._session.commit()
            logger.info("supply_updated supply_id=%s", supply.id)
            if was_active and not supply.active:
                logger.info("supply_deactivated supply_id=%s", supply.id)
            return supply
        except (SupplyNotFoundError, BaseUnitLockedError):
            self._session.rollback()
            raise
        except IntegrityError as error:
            self._session.rollback()
            raise DuplicateSupplySkuError("El SKU ya está registrado") from error
        except SQLAlchemyError as error:
            self._rollback("supply_update_failed", error)
            raise PersistenceError("No se pudo actualizar el insumo") from error

    def add_presentation(
        self, supply_id: UUID, payload: PresentationCreate
    ) -> SupplyPresentation:
        try:
            supply = self.get(supply_id)
            UnitConversionService.convert(
                payload.quantity, payload.unit, SupplyUnit(supply.base_unit)
            )
            data = payload.model_dump(exclude={"unit"})
            presentation = SupplyPresentation(
                **data,
                supply_id=supply.id,
                unit=payload.unit.value,
            )
            self._presentations.add(presentation)
            self._session.commit()
            return presentation
        except SupplyNotFoundError:
            self._session.rollback()
            raise
        except SQLAlchemyError as error:
            self._rollback("supply_presentation_failed", error)
            raise PersistenceError("No se pudo guardar la presentación") from error

    def list_presentations(self, supply_id: UUID) -> list[SupplyPresentation]:
        self.get(supply_id)
        return self._presentations.list(supply_id)

    def record_purchase(
        self, supply_id: UUID, payload: PurchaseCreate
    ) -> SupplyPurchase:
        try:
            supply = self._lock_supply(supply_id)
            base_quantity = payload.quantity
            if payload.presentation_id is not None:
                presentation = self._get_presentation(
                    supply.id, payload.presentation_id
                )
                presentation_base_quantity = UnitConversionService.convert(
                    presentation.quantity,
                    SupplyUnit(presentation.unit),
                    SupplyUnit(supply.base_unit),
                )
                base_quantity *= presentation_base_quantity
            purchase = SupplyPurchase(
                supply_id=supply.id,
                presentation_id=payload.presentation_id,
                quantity=base_quantity,
                total_cost=payload.total_cost,
                currency=payload.currency,
                purchased_at=payload.purchased_at,
                notes=payload.notes,
            )
            self._purchases.add(purchase)
            self._movements.add(
                SupplyStockMovement(
                    supply_id=supply.id,
                    movement_type=MovementType.PURCHASE.value,
                    purchase_id=purchase.id,
                    quantity=base_quantity,
                    occurred_at=payload.purchased_at,
                    notes=None,
                )
            )
            self._session.commit()
            logger.info("supply_purchase_recorded supply_id=%s", supply.id)
            return purchase
        except (SupplyNotFoundError, PresentationNotFoundError):
            self._session.rollback()
            raise
        except SQLAlchemyError as error:
            self._rollback("supply_purchase_failed", error)
            raise PersistenceError("No se pudo registrar la compra") from error

    def list_purchases(self, supply_id: UUID) -> list[SupplyPurchase]:
        self.get(supply_id)
        return self._purchases.list(supply_id)

    def stock(self, supply_id: UUID) -> StockRead:
        supply = self.get(supply_id)
        return StockRead(
            supply_id=supply.id,
            quantity=self._movements.stock(supply.id),
            unit=SupplyUnit(supply.base_unit),
        )

    def adjust(self, supply_id: UUID, payload: AdjustmentCreate) -> SupplyStockMovement:
        try:
            supply = self._lock_supply(supply_id)
            signed_quantity = payload.quantity
            movement_type = MovementType.ADJUSTMENT_IN
            if payload.direction is AdjustmentDirection.OUT:
                available = self._movements.stock(supply.id)
                if payload.quantity > available:
                    logger.warning(
                        "insufficient_stock_rejected supply_id=%s", supply.id
                    )
                    raise InsufficientStockError(
                        "La existencia disponible es insuficiente"
                    )
                signed_quantity = -payload.quantity
                movement_type = MovementType.ADJUSTMENT_OUT
            movement = SupplyStockMovement(
                supply_id=supply.id,
                movement_type=movement_type.value,
                quantity=signed_quantity,
                occurred_at=payload.occurred_at,
                notes=payload.reason,
            )
            self._movements.add(movement)
            self._session.commit()
            logger.info("stock_adjusted supply_id=%s", supply.id)
            return movement
        except (SupplyNotFoundError, InsufficientStockError):
            self._session.rollback()
            raise
        except SQLAlchemyError as error:
            self._rollback("stock_adjustment_failed", error)
            raise PersistenceError("No se pudo ajustar el stock") from error

    def list_movements(self, supply_id: UUID) -> list[SupplyStockMovement]:
        self.get(supply_id)
        return self._movements.list(supply_id)

    def estimated_cost(self, supply_id: UUID) -> EstimatedCostRead:
        supply = self.get(supply_id)
        purchase = self._purchases.latest(supply.id)
        if purchase is None:
            raise EstimatedCostUnavailableError(
                "No existen compras para estimar el costo"
            )
        return EstimatedCostRead(
            supply_id=supply.id,
            unit=SupplyUnit(supply.base_unit),
            currency=purchase.currency,
            unit_cost=purchase.total_cost / purchase.quantity,
        )

    def _lock_supply(self, supply_id: UUID) -> Supply:
        supply = self._supplies.get(supply_id, for_update=True)
        if supply is None:
            raise SupplyNotFoundError("No existe el insumo solicitado")
        return supply

    def _get_presentation(
        self, supply_id: UUID, presentation_id: UUID
    ) -> SupplyPresentation:
        presentation = self._presentations.get(presentation_id)
        if presentation is None or presentation.supply_id != supply_id:
            raise PresentationNotFoundError(
                "La presentación no pertenece al insumo solicitado"
            )
        return presentation

    def _rollback(self, event: str, error: SQLAlchemyError) -> None:
        self._session.rollback()
        logger.error("%s (%s); rollback ejecutado", event, type(error).__name__)
