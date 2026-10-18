"""Simulación pura: reconstruye capas sin asignar consumos persistentes."""

from collections import deque
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass
class FifoLayer:
    quantity: Decimal
    movement_id: UUID | None
    purchase_id: UUID | None
    unit_cost: Decimal | None
    currency: str | None


class FifoPool:
    def __init__(self) -> None:
        self.layers: deque[FifoLayer] = deque()
        self.debt = Decimal(0)

    def add(self, layer: FifoLayer) -> None:
        covered = min(layer.quantity, self.debt)
        self.debt -= covered
        layer.quantity -= covered
        if layer.quantity:
            self.layers.append(layer)

    def take(self, quantity: Decimal) -> list[FifoLayer]:
        result: list[FifoLayer] = []
        while quantity and self.layers:
            layer = self.layers[0]
            used = min(quantity, layer.quantity)
            result.append(
                FifoLayer(
                    used,
                    layer.movement_id,
                    layer.purchase_id,
                    layer.unit_cost,
                    layer.currency,
                )
            )
            quantity -= used
            layer.quantity -= used
            if not layer.quantity:
                self.layers.popleft()
        if quantity:
            self.debt += quantity
            result.append(FifoLayer(quantity, None, None, None, None))
        return result
