from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.production.run_models import ProductionRun
from app.modules.products.consumption_models import ProductionRunProductConsumption
from app.modules.products.consumption_schemas import RunProductConsumptionCreate
from app.modules.products.exceptions import ProductNotFoundError
from app.modules.products.models import ProductVariant
from app.modules.products.stock_models import ProductStockMovement
from app.modules.products.stock_service import ProductStockConflictError


class RunProductConsumptionService:
    """Consumos y salida se confirman en la transacción del Run."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_for_run(self, run_id: UUID) -> list[ProductionRunProductConsumption]:
        return list(
            self.session.scalars(
                select(ProductionRunProductConsumption)
                .where(ProductionRunProductConsumption.run_id == run_id)
                .order_by(ProductionRunProductConsumption.variant_id)
            )
        )

    def record(
        self,
        run: ProductionRun,
        items: list[RunProductConsumptionCreate],
        occurred_at: datetime,
    ) -> None:
        ids = {item.variant_id for item in items}
        if run.output_variant_id in ids:
            raise ProductStockConflictError(
                "El producto de salida no puede consumirse como componente de sí mismo"
            )
        # Incluir salida en el mismo orden de bloqueos evita A→B/B→A concurrentes.
        if run.output_variant_id is not None:
            ids.add(run.output_variant_id)
        if not ids:
            return
        variants = {
            variant.id: variant
            for variant in self.session.scalars(
                select(ProductVariant)
                .where(ProductVariant.id.in_(ids))
                .order_by(ProductVariant.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        }
        if set(variants) != ids:
            raise ProductNotFoundError("Una variante del consumo real no existe")
        for item in items:
            consumption = ProductionRunProductConsumption(
                run_id=run.id,
                variant_id=item.variant_id,
                consumed=item.consumed,
                wasted=item.wasted,
                unit=variants[item.variant_id].base_unit,
            )
            self.session.add(consumption)
            self.session.flush()
            self.session.add(
                ProductStockMovement(
                    variant_id=item.variant_id,
                    quantity=-item.consumed,
                    unit=consumption.unit,
                    movement_type="consumption",
                    run_consumption_id=consumption.id,
                    occurred_at=occurred_at,
                )
            )
        self.session.flush()
