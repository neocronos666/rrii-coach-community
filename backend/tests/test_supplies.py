from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.modules.supplies.conversion import UnitConversionService
from app.modules.supplies.exceptions import (
    BaseUnitLockedError,
    EstimatedCostUnavailableError,
    InsufficientStockError,
    UnitConversionError,
)
from app.modules.supplies.models import Supply, SupplyPresentation, SupplyPurchase
from app.modules.supplies.repository import (
    StockMovementRepository,
    SupplyPresentationRepository,
    SupplyPurchaseRepository,
    SupplyRepository,
)
from app.modules.supplies.schemas import (
    AdjustmentCreate,
    AdjustmentDirection,
    PresentationCreate,
    PurchaseCreate,
    SupplyCategory,
    SupplyCreate,
    SupplyUnit,
    SupplyUpdate,
)
from app.modules.supplies.service import SupplyService


def build_service() -> tuple[
    SupplyService, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock
]:
    session = MagicMock(spec=Session)
    supplies = MagicMock(spec=SupplyRepository)
    supplies.has_production_references.return_value = False
    presentations = MagicMock(spec=SupplyPresentationRepository)
    purchases = MagicMock(spec=SupplyPurchaseRepository)
    movements = MagicMock(spec=StockMovementRepository)
    return (
        SupplyService(session, supplies, presentations, purchases, movements),
        supplies,
        presentations,
        purchases,
        movements,
        session,
    )


def supply(*, base_unit: str = "g") -> Supply:
    return Supply(
        id=uuid4(),
        name="PLA Negro",
        sku="PLA-NEG-001",
        category="material",
        base_unit=base_unit,
        active=True,
    )


def apply_changes(value: Supply, changes: dict[str, object]) -> Supply:
    for field_name, field_value in changes.items():
        setattr(value, field_name, field_value)
    return value


@pytest.mark.parametrize(
    ("quantity", "source", "target", "expected"),
    [
        ("1", SupplyUnit.KILOGRAM, SupplyUnit.GRAM, "1000"),
        ("1", SupplyUnit.LITER, SupplyUnit.MILLILITER, "1000"),
        ("1", SupplyUnit.METER, SupplyUnit.CENTIMETER, "100"),
    ],
)
def test_unit_conversion(
    quantity: str, source: SupplyUnit, target: SupplyUnit, expected: str
) -> None:
    assert UnitConversionService.convert(Decimal(quantity), source, target) == Decimal(
        expected
    )


def test_incompatible_unit_conversion_is_rejected() -> None:
    with pytest.raises(UnitConversionError):
        UnitConversionService.convert(
            Decimal("1"), SupplyUnit.GRAM, SupplyUnit.MILLILITER
        )


def test_supply_schema_categories_units_and_decimal_validation() -> None:
    payload = SupplyCreate(
        name="Resina", category=SupplyCategory.MATERIAL, base_unit=SupplyUnit.MILLILITER
    )
    assert payload.active is True
    with pytest.raises(ValidationError):
        PresentationCreate(
            name="Inválida", quantity=Decimal("0"), unit=SupplyUnit.LITER
        )


def test_base_unit_can_change_before_movements() -> None:
    service, supplies, _, _, _, session = build_service()
    current = supply()
    supplies.get.return_value = current
    supplies.has_movements.return_value = False
    supplies.update.side_effect = apply_changes

    updated = service.update(current.id, SupplyUpdate(base_unit=SupplyUnit.KILOGRAM))

    assert updated.base_unit == "kg"
    session.commit.assert_called_once_with()


def test_base_unit_is_locked_after_movement() -> None:
    service, supplies, _, _, _, session = build_service()
    current = supply()
    supplies.get.return_value = current
    supplies.has_movements.return_value = True

    with pytest.raises(BaseUnitLockedError):
        service.update(current.id, SupplyUpdate(base_unit=SupplyUnit.KILOGRAM))

    supplies.update.assert_not_called()
    session.rollback.assert_called_once_with()


def test_purchase_presentation_creates_normalized_movement() -> None:
    service, supplies, presentations, purchases, movements, session = build_service()
    current = supply()
    supplies.get.return_value = current
    presentation = SupplyPresentation(
        id=uuid4(),
        supply_id=current.id,
        name="Rollo 1 kg",
        quantity=Decimal("1"),
        unit="kg",
        active=True,
    )
    presentations.get.return_value = presentation
    purchases.add.side_effect = lambda value: value
    movements.add.side_effect = lambda value: value

    purchase = service.record_purchase(
        current.id,
        PurchaseCreate(
            quantity=Decimal("2"),
            presentation_id=presentation.id,
            total_cost=Decimal("36000"),
            currency="ARS",
            purchased_at=datetime.now(UTC),
        ),
    )

    assert purchase.quantity == Decimal("2000")
    assert movements.add.call_args.args[0].quantity == Decimal("2000")
    session.commit.assert_called_once_with()


def test_stock_ledger_and_insufficient_outgoing() -> None:
    service, supplies, _, _, movements, session = build_service()
    current = supply()
    supplies.get.return_value = current
    movements.stock.return_value = Decimal("100")

    with pytest.raises(InsufficientStockError):
        service.adjust(
            current.id,
            AdjustmentCreate(
                direction=AdjustmentDirection.OUT,
                quantity=Decimal("101"),
                reason="Corrección",
                occurred_at=datetime.now(UTC),
            ),
        )

    movements.add.assert_not_called()
    session.rollback.assert_called_once_with()


def test_estimated_cost_uses_latest_purchase_currency() -> None:
    service, supplies, _, purchases, _, _ = build_service()
    current = supply()
    supplies.get.return_value = current
    purchases.latest.return_value = SupplyPurchase(
        supply_id=current.id,
        quantity=Decimal("1000"),
        total_cost=Decimal("18000"),
        currency="ARS",
        purchased_at=datetime.now(UTC),
    )

    estimated = service.estimated_cost(current.id)

    assert estimated.unit_cost == Decimal("18")
    assert estimated.currency == "ARS"


def test_estimated_cost_without_purchases_is_unavailable() -> None:
    service, supplies, _, purchases, _, _ = build_service()
    current = supply()
    supplies.get.return_value = current
    purchases.latest.return_value = None

    with pytest.raises(EstimatedCostUnavailableError):
        service.estimated_cost(current.id)
