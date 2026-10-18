from decimal import Decimal

import pytest

from app.modules.costing.calculator import TechnicalCostCalculator
from app.modules.costing.exceptions import CurrencyMismatchError
from app.modules.costing.types import Money, ResolvedCostItem


def item(
    *,
    description: str,
    quantity: str,
    unit_cost: str | None,
    currency: str | None = "ARS",
    category: str = "material",
    unit: str = "g",
) -> ResolvedCostItem:
    return ResolvedCostItem(
        category=category,
        description=description,
        quantity=Decimal(quantity),
        unit=unit,
        unit_cost=Decimal(unit_cost) if unit_cost is not None else None,
        currency=currency if unit_cost is not None else None,
        source="test" if unit_cost is not None else "unavailable",
        warning="Fuente no configurada" if unit_cost is None else None,
    )


def test_material_cost_uses_decimal() -> None:
    result = TechnicalCostCalculator().calculate(
        [item(description="PLA", quantity="83.4", unit_cost="18")]
    )
    assert result.lines[0].subtotal == Decimal("1501.2000")
    assert result.totals_by_currency == {"ARS": Decimal("1501.2000")}


def test_labor_half_hour() -> None:
    result = TechnicalCostCalculator().calculate(
        [
            item(
                description="Posproducción",
                quantity="0.5",
                unit_cost="6000",
                category="postproduction_labor",
                unit="h",
            )
        ]
    )
    assert result.lines[0].subtotal == Decimal("3000.0000")


def test_explicit_energy_cost() -> None:
    result = TechnicalCostCalculator().calculate(
        [
            item(
                description="Electricidad",
                quantity="0.7",
                unit_cost="180",
                category="energy",
                unit="kWh",
            )
        ]
    )
    assert result.lines[0].subtotal == Decimal("126.0000")


def test_energy_estimate_and_depreciation() -> None:
    calculator = TechnicalCostCalculator()
    hours = calculator.hours_from_minutes(120)
    assert calculator.estimated_energy_kwh(Decimal("350"), hours) == Decimal("0.7")
    depreciation = calculator.basic_depreciation_hourly(
        Decimal("500000"), Decimal("10000")
    )
    result = calculator.calculate(
        [
            item(
                description="Máquina",
                quantity=str(hours),
                unit_cost=str(depreciation),
                category="machine_time",
                unit="h",
            )
        ]
    )
    assert result.lines[0].subtotal == Decimal("100.0000")


def test_missing_source_marks_breakdown_incomplete() -> None:
    result = TechnicalCostCalculator().calculate(
        [item(description="Sin costo", quantity="1", unit_cost=None)]
    )
    assert result.complete is False
    assert result.lines[0].subtotal is None
    assert result.warnings == ("Fuente no configurada",)


def test_multi_currency_keeps_separate_totals_and_manual_extra() -> None:
    result = TechnicalCostCalculator().calculate(
        [
            item(description="Local", quantity="1", unit_cost="100"),
            item(
                description="Extra manual",
                quantity="1",
                unit_cost="20",
                currency="USD",
                category="extra",
                unit="item",
            ),
        ]
    )
    assert result.multi_currency is True
    assert result.totals_by_currency == {
        "ARS": Decimal("100.0000"),
        "USD": Decimal("20.0000"),
    }


def test_money_rejects_currency_mismatch() -> None:
    assert Money(Decimal("100"), "ARS") + Money(Decimal("50"), "ARS") == Money(
        Decimal("150"), "ARS"
    )
    with pytest.raises(CurrencyMismatchError):
        Money(Decimal("100"), "ARS") + Money(Decimal("20"), "USD")
