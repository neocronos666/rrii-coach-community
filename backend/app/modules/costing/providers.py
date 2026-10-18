from typing import Protocol
from uuid import UUID

from app.modules.costing.types import CostQuote
from app.modules.supplies.repository import SupplyPurchaseRepository


class SupplyCostProvider(Protocol):
    def get_unit_cost(self, supply_id: UUID, unit: str) -> CostQuote | None: ...


class LastPurchaseSupplyCostProvider:
    """Fuente Community basada en la última compra por fecha efectiva."""

    def __init__(self, purchases: SupplyPurchaseRepository) -> None:
        self._purchases = purchases

    def get_unit_cost(self, supply_id: UUID, unit: str) -> CostQuote | None:
        purchase = self._purchases.latest(supply_id)
        if purchase is None:
            return None
        return CostQuote(
            amount=purchase.total_cost / purchase.quantity,
            currency=purchase.currency,
            unit=unit,
            source="last_purchase",
            source_reference=str(purchase.id),
            as_of=purchase.purchased_at,
        )
