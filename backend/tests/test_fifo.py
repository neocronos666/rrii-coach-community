from decimal import Decimal
from uuid import uuid4

from app.modules.costing.fifo import FifoLayer, FifoPool


def layer(quantity: str, cost: str | None = None) -> FifoLayer:
    return FifoLayer(
        Decimal(quantity),
        uuid4(),
        uuid4() if cost else None,
        Decimal(cost) if cost else None,
        "ARS" if cost else None,
    )


def test_layers_partial_consumption_and_shortage() -> None:
    pool = FifoPool()
    pool.add(layer("10", "2"))
    pool.add(layer("10", "3"))
    pool.take(Decimal(4))
    result = pool.take(Decimal(12))
    assert [(row.quantity, row.unit_cost) for row in result] == [
        (Decimal(6), Decimal(2)),
        (Decimal(6), Decimal(3)),
    ]
    result = pool.take(Decimal(8))
    assert [(row.quantity, row.unit_cost) for row in result] == [
        (Decimal(4), Decimal(3)),
        (Decimal(4), None),
    ]
    assert pool.debt == 4


def test_debt_uses_replenishment_before_new_demand() -> None:
    pool = FifoPool()
    pool.take(Decimal(8))
    pool.add(layer("3", "4"))
    pool.add(layer("10", "5"))
    assert pool.debt == 0
    result = pool.take(Decimal(6))
    assert [(row.quantity, row.unit_cost) for row in result] == [
        (Decimal(5), Decimal(5)),
        (Decimal(1), None),
    ]


def test_unknown_layer_is_not_skipped() -> None:
    pool = FifoPool()
    pool.add(layer("5"))
    pool.add(layer("5", "7"))
    assert pool.take(Decimal(3))[0].unit_cost is None
    assert pool.take(Decimal(3))[1].unit_cost == 7
