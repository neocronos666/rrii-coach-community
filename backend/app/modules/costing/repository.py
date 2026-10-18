from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.costing.models import CostCalculation


class CostCalculationRepository:
    """Persistencia de snapshots, sin confirmar ni revertir transacciones."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, calculation: CostCalculation) -> CostCalculation:
        self._session.add(calculation)
        self._session.flush()
        return calculation

    def get(self, calculation_id: UUID) -> CostCalculation | None:
        statement = (
            select(CostCalculation)
            .options(selectinload(CostCalculation.lines))
            .where(CostCalculation.id == calculation_id)
        )
        return self._session.scalar(statement)
