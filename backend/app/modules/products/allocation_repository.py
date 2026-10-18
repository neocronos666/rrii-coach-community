from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.modules.products.allocation_models import ProductStockAllocation
from app.modules.projects.models import ProjectComponent


class ProductAllocationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def reserved(self, variant_id: UUID) -> Decimal:
        return Decimal(
            self.session.scalar(
                select(
                    func.coalesce(func.sum(ProductStockAllocation.quantity), 0)
                ).where(ProductStockAllocation.variant_id == variant_id)
            )
            or 0
        )

    def release_order(self, order_id: UUID) -> None:
        self.session.execute(
            update(ProductStockAllocation)
            .where(ProductStockAllocation.order_id == order_id)
            .values(quantity=Decimal(0))
        )

    def release_project(self, project_id: UUID) -> None:
        components = select(ProjectComponent.id).where(
            ProjectComponent.project_id == project_id
        )
        self.session.execute(
            update(ProductStockAllocation)
            .where(ProductStockAllocation.project_component_id.in_(components))
            .values(quantity=Decimal(0))
        )
