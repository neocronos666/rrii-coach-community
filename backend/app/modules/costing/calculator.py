from decimal import Decimal

from app.modules.costing.types import (
    CalculatedBreakdown,
    CalculatedCostLine,
    ResolvedCostItem,
    monetary_snapshot,
    unit_cost_snapshot,
)


class TechnicalCostCalculator:
    """Aritmética pura sobre costos ya resueltos, sin I/O ni persistencia."""

    def calculate(self, items: list[ResolvedCostItem]) -> CalculatedBreakdown:
        lines: list[CalculatedCostLine] = []
        totals: dict[str, Decimal] = {}
        warnings: list[str] = []
        for item in items:
            complete = item.unit_cost is not None and item.currency is not None
            subtotal: Decimal | None = None
            snapshot_unit_cost: Decimal | None = None
            if complete:
                assert item.unit_cost is not None
                assert item.currency is not None
                snapshot_unit_cost = unit_cost_snapshot(item.unit_cost)
                subtotal = monetary_snapshot(item.quantity * item.unit_cost)
                totals[item.currency] = totals.get(item.currency, Decimal(0)) + subtotal
            if item.warning is not None:
                warnings.append(item.warning)
            lines.append(
                CalculatedCostLine(
                    category=item.category,
                    description=item.description,
                    quantity=item.quantity,
                    unit=item.unit,
                    unit_cost=snapshot_unit_cost,
                    currency=item.currency,
                    subtotal=subtotal,
                    source=item.source,
                    source_reference=item.source_reference,
                    complete=complete,
                )
            )
        currencies = {line.currency for line in lines if line.currency is not None}
        return CalculatedBreakdown(
            lines=tuple(lines),
            totals_by_currency={
                currency: monetary_snapshot(total) for currency, total in totals.items()
            },
            complete=all(line.complete for line in lines),
            multi_currency=len(currencies) > 1,
            warnings=tuple(warnings),
        )

    @staticmethod
    def hours_from_minutes(minutes: int) -> Decimal:
        return Decimal(minutes) / Decimal(60)

    @staticmethod
    def estimated_energy_kwh(rated_power_w: Decimal, hours: Decimal) -> Decimal:
        return rated_power_w * hours / Decimal(1000)

    @staticmethod
    def basic_depreciation_hourly(
        purchase_price: Decimal, useful_life_hours: Decimal
    ) -> Decimal:
        return purchase_price / useful_life_hours
