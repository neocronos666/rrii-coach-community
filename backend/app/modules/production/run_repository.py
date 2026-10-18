from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.production.run_models import ProductionRun


class ProductionRunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, run_id: UUID, *, lock: bool = False) -> ProductionRun | None:
        statement = select(ProductionRun).where(ProductionRun.id == run_id)
        if lock:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return self.session.scalar(statement)

    def by_request(self, request_id: UUID) -> ProductionRun | None:
        return self.session.scalar(
            select(ProductionRun).where(ProductionRun.request_id == request_id)
        )

    def open_for_task(self, task_id: UUID) -> ProductionRun | None:
        return self.session.scalar(
            select(ProductionRun).where(
                ProductionRun.task_id == task_id, ProductionRun.status == "running"
            )
        )

    def list(self, task_id: UUID) -> list[ProductionRun]:
        return list(
            self.session.scalars(
                select(ProductionRun)
                .where(ProductionRun.task_id == task_id)
                .order_by(ProductionRun.started_at, ProductionRun.id)
            )
        )

    def totals(self, task_id: UUID) -> tuple[Decimal, Decimal, int]:
        row = self.session.execute(
            select(
                func.coalesce(func.sum(ProductionRun.good_quantity), 0),
                func.coalesce(func.sum(ProductionRun.failed_quantity), 0),
                func.count(),
            ).where(ProductionRun.task_id == task_id, ProductionRun.status == "closed")
        ).one()
        return Decimal(row[0]), Decimal(row[1]), int(row[2])
