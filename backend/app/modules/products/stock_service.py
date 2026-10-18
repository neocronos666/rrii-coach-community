from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.modules.production.run_models import ProductionRun
from app.modules.products.allocation_repository import ProductAllocationRepository
from app.modules.products.exceptions import ProductNotFoundError
from app.modules.products.repository import ProductRepository
from app.modules.products.stock_models import ProductStockMovement
from app.modules.products.stock_schemas import ProductStockRead, StockMovementCreate


class ProductStockConflictError(Exception):
    pass


class ProductStockService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.products = ProductRepository(session)

    def stock(self, variant_id: UUID) -> ProductStockRead:
        variant = self.products.variant(variant_id, lock=True)
        if variant is None:
            raise ProductNotFoundError("No existe la variante")
        quantity = self.session.scalar(
            select(func.coalesce(func.sum(ProductStockMovement.quantity), 0)).where(
                ProductStockMovement.variant_id == variant_id
            )
        )
        physical = Decimal(quantity or 0)
        reserved = ProductAllocationRepository(self.session).reserved(variant_id)
        return ProductStockRead(
            variant_id=variant_id,
            unit=variant.base_unit,
            physical_quantity=physical,
            allocated_quantity=reserved,
            available_quantity=physical - reserved,
            shortage_warning=physical - reserved < 0,
        )

    def movements(
        self, variant_id: UUID, offset: int, limit: int
    ) -> list[ProductStockMovement]:
        if self.products.variant(variant_id) is None:
            raise ProductNotFoundError("No existe la variante")
        return list(
            self.session.scalars(
                select(ProductStockMovement)
                .where(ProductStockMovement.variant_id == variant_id)
                .order_by(ProductStockMovement.occurred_at, ProductStockMovement.id)
                .offset(offset)
                .limit(limit)
            )
        )

    def create(
        self, variant_id: UUID, payload: StockMovementCreate
    ) -> ProductStockMovement:
        try:
            variant = self.products.variant(variant_id, lock=True)
            if variant is None:
                raise ProductNotFoundError("No existe la variante")
            original = self.session.scalar(
                select(ProductStockMovement).where(
                    ProductStockMovement.request_id == payload.request_id
                )
            )
            request = payload.model_dump(mode="json")
            if original:
                if (
                    original.variant_id != variant_id
                    or original.request_payload != request
                ):
                    raise ProductStockConflictError(
                        "La petición ya tiene otro movimiento"
                    )
                return original
            now = datetime.now(UTC)
            occurred_at = payload.occurred_at or now
            if occurred_at > now:
                raise ProductStockConflictError(
                    "El movimiento no puede estar en el futuro"
                )
            movement = ProductStockMovement(
                variant_id=variant_id,
                quantity=-payload.quantity
                if payload.movement_type == "adjustment_out"
                else payload.quantity,
                unit=variant.base_unit,
                movement_type=payload.movement_type,
                request_id=payload.request_id,
                request_payload=request,
                reason=payload.reason,
                occurred_at=occurred_at,
            )
            self.session.add(movement)
            self.session.commit()
            self.session.refresh(movement)
            return movement
        except (ProductNotFoundError, ProductStockConflictError):
            self.session.rollback()
            raise
        except IntegrityError as error:
            self.session.rollback()
            raise ProductStockConflictError(
                "Conflicto de petición concurrente"
            ) from error
        except SQLAlchemyError as error:
            self.session.rollback()
            raise PersistenceError("No se pudo registrar el movimiento") from error

    def record_production(self, run: ProductionRun) -> None:
        """Parte de la transacción de cierre; no confirma por separado."""
        if (
            run.test_print_step_id is not None
            or run.output_variant_id is None
            or not run.good_quantity
        ):
            return
        variant = self.products.variant(run.output_variant_id, lock=True)
        if variant is None or variant.base_unit != run.unit:
            raise ProductStockConflictError(
                "La salida no coincide con la unidad de la variante"
            )
        self.session.add(
            ProductStockMovement(
                variant_id=variant.id,
                quantity=run.good_quantity,
                unit=variant.base_unit,
                movement_type="production",
                run_id=run.id,
                occurred_at=run.ended_at,
            )
        )
        self.session.flush()
