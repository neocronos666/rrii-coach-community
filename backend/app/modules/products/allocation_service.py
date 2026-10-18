from datetime import UTC, datetime
from decimal import Decimal
from typing import NoReturn
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.modules.orders.models import Order
from app.modules.products.allocation_models import ProductStockAllocation
from app.modules.products.allocation_schemas import AllocationCreate, AllocationDelivery
from app.modules.products.exceptions import ProductNotFoundError
from app.modules.products.repository import ProductRepository
from app.modules.products.stock_models import ProductStockMovement
from app.modules.products.stock_service import ProductStockConflictError
from app.modules.projects.models import Project, ProjectComponent


class ProductAllocationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.products = ProductRepository(session)

    def get(self, allocation_id: UUID, *, lock: bool = False) -> ProductStockAllocation:
        statement = select(ProductStockAllocation).where(
            ProductStockAllocation.id == allocation_id
        )
        if lock:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        allocation = self.session.scalar(statement)
        if allocation is None:
            raise ProductNotFoundError("No existe la asignación")
        return allocation

    def list_allocations(
        self,
        order_id: UUID | None,
        project_component_id: UUID | None,
        offset: int,
        limit: int,
    ) -> list[ProductStockAllocation]:
        statement = select(ProductStockAllocation)
        if order_id is not None:
            statement = statement.where(ProductStockAllocation.order_id == order_id)
        if project_component_id is not None:
            statement = statement.where(
                ProductStockAllocation.project_component_id == project_component_id
            )
        return list(
            self.session.scalars(
                statement.order_by(
                    ProductStockAllocation.created_at, ProductStockAllocation.id
                )
                .offset(offset)
                .limit(limit)
            )
        )

    def validate_destination(
        self,
        order_id: UUID | None,
        component_id: UUID | None,
        *,
        require_active: bool = True,
    ) -> None:
        parent: Order | Project | None
        if order_id is not None:
            parent = self.session.scalar(
                select(Order)
                .where(Order.id == order_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        else:
            parent = self.session.scalar(
                select(Project)
                .join(ProjectComponent)
                .where(ProjectComponent.id == component_id)
                .with_for_update(of=Project)
                .execution_options(populate_existing=True)
            )
        if parent is None:
            raise ProductNotFoundError("No existe el destino de la asignación")
        if require_active and parent.status == "cancelled":
            raise ProductStockConflictError("El destino está cancelado")

    def create(self, payload: AllocationCreate) -> ProductStockAllocation:
        try:
            self.validate_destination(
                payload.order_id, payload.project_component_id, require_active=False
            )
            variant = self.products.variant(payload.variant_id, lock=True)
            if variant is None:
                raise ProductNotFoundError("No existe la variante")
            original = self.session.scalar(
                select(ProductStockAllocation).where(
                    ProductStockAllocation.request_id == payload.request_id
                )
            )
            if original is not None:
                if AllocationCreate.model_validate(original.request_payload) != payload:
                    raise ProductStockConflictError(
                        "La petición corresponde a otra asignación"
                    )
                return original
            self.validate_destination(payload.order_id, payload.project_component_id)
            allocation = ProductStockAllocation(
                variant_id=variant.id,
                order_id=payload.order_id,
                project_component_id=payload.project_component_id,
                quantity=payload.quantity,
                initial_quantity=payload.quantity,
                unit=variant.base_unit,
                request_id=payload.request_id,
                request_payload=payload.model_dump(mode="json"),
            )
            self.session.add(allocation)
            self.session.commit()
            self.session.refresh(allocation)
            return allocation
        except (ProductNotFoundError, ProductStockConflictError):
            self.session.rollback()
            raise
        except SQLAlchemyError as error:
            self._failure(error)

    def release(self, allocation_id: UUID) -> ProductStockAllocation:
        try:
            existing = self.get(allocation_id)
            self.validate_destination(
                existing.order_id, existing.project_component_id, require_active=False
            )
            self.products.variant(existing.variant_id, lock=True)
            allocation = self.get(allocation_id, lock=True)
            allocation.quantity = Decimal(0)
            self.session.commit()
            self.session.refresh(allocation)
            return allocation
        except (ProductNotFoundError, ProductStockConflictError):
            self.session.rollback()
            raise
        except SQLAlchemyError as error:
            self._failure(error)

    def deliver(
        self, allocation_id: UUID, payload: AllocationDelivery
    ) -> ProductStockMovement:
        try:
            existing = self.get(allocation_id)
            self.validate_destination(
                existing.order_id, existing.project_component_id, require_active=False
            )
            self.products.variant(existing.variant_id, lock=True)
            allocation = self.get(allocation_id, lock=True)
            original = self.session.scalar(
                select(ProductStockMovement).where(
                    ProductStockMovement.request_id == payload.request_id
                )
            )
            if original is not None:
                if (
                    original.allocation_id != allocation_id
                    or original.request_payload is None
                    or AllocationDelivery.model_validate(original.request_payload)
                    != payload
                ):
                    raise ProductStockConflictError(
                        "La petición corresponde a otra salida"
                    )
                return original
            self.validate_destination(
                allocation.order_id, allocation.project_component_id
            )
            if payload.quantity > allocation.quantity:
                raise ProductStockConflictError(
                    "La entrega supera la cantidad pendiente asignada"
                )
            allocation.quantity -= payload.quantity
            movement = ProductStockMovement(
                variant_id=allocation.variant_id,
                quantity=-payload.quantity,
                unit=allocation.unit,
                movement_type="delivery",
                allocation_id=allocation.id,
                request_id=payload.request_id,
                request_payload=payload.model_dump(mode="json"),
                occurred_at=datetime.now(UTC),
            )
            self.session.add(movement)
            self.session.commit()
            self.session.refresh(movement)
            return movement
        except (ProductNotFoundError, ProductStockConflictError):
            self.session.rollback()
            raise
        except SQLAlchemyError as error:
            self._failure(error)

    def _failure(self, error: SQLAlchemyError) -> NoReturn:
        self.session.rollback()
        if isinstance(error, IntegrityError):
            raise ProductStockConflictError(
                "Conflicto concurrente de asignación"
            ) from error
        raise PersistenceError("No se pudo registrar la asignación") from error
