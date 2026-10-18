from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.production.run_models import ProductionRun
from app.modules.supplies.consumption_models import ProductionRunSupplyConsumption
from app.modules.supplies.consumption_schemas import RunSupplyConsumptionCreate
from app.modules.supplies.exceptions import SupplyNotFoundError
from app.modules.supplies.models import Supply, SupplyStockMovement
from app.modules.supplies.repository import StockMovementRepository
from app.modules.supplies.reservation_repository import SupplyReservationRepository


class RunSupplyConsumptionService:
    """Participa en la transacción de cierre del Run; no confirma por separado."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_for_run(self, run_id: UUID) -> list[ProductionRunSupplyConsumption]:
        return list(
            self.session.scalars(
                select(ProductionRunSupplyConsumption)
                .where(ProductionRunSupplyConsumption.run_id == run_id)
                .order_by(ProductionRunSupplyConsumption.supply_id)
            )
        )

    def record(
        self,
        run: ProductionRun,
        items: list[RunSupplyConsumptionCreate],
        occurred_at: datetime,
    ) -> None:
        ids = {item.supply_id for item in items}
        if not ids:
            return
        supplies = {
            supply.id: supply
            for supply in self.session.scalars(
                select(Supply)
                .where(Supply.id.in_(ids))
                .order_by(Supply.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        }
        if set(supplies) != ids:
            raise SupplyNotFoundError("Un insumo del consumo real no existe")
        reservations = SupplyReservationRepository(self.session)
        movements = StockMovementRepository(self.session)
        for item in items:
            consumption = ProductionRunSupplyConsumption(
                run_id=run.id,
                supply_id=item.supply_id,
                consumed=item.consumed,
                wasted=item.wasted,
                unit=supplies[item.supply_id].base_unit,
            )
            self.session.add(consumption)
            self.session.flush()
            movements.add(
                SupplyStockMovement(
                    supply_id=item.supply_id,
                    movement_type="consumption",
                    quantity=-item.consumed,
                    run_consumption_id=consumption.id,
                    occurred_at=occurred_at,
                    notes="Consumo real de producción",
                )
            )
            reservation = (
                reservations.get(run.task_id, item.supply_id)
                if run.task_id is not None
                else None
            )
            if reservation is not None:
                reservation.quantity = max(
                    Decimal(0), reservation.quantity - item.consumed
                )
        self.session.flush()
