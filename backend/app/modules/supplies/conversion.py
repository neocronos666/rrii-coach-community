from decimal import Decimal
from typing import ClassVar

from app.modules.supplies.exceptions import UnitConversionError
from app.modules.supplies.schemas import SupplyUnit


class UnitConversionService:
    """Conversiones exactas y acotadas dentro de una misma dimensión."""

    _factors: ClassVar[dict[SupplyUnit, tuple[str, Decimal]]] = {
        SupplyUnit.UNIT: ("count", Decimal("1")),
        SupplyUnit.GRAM: ("mass", Decimal("1")),
        SupplyUnit.KILOGRAM: ("mass", Decimal("1000")),
        SupplyUnit.MILLILITER: ("volume", Decimal("1")),
        SupplyUnit.LITER: ("volume", Decimal("1000")),
        SupplyUnit.MILLIMETER: ("length", Decimal("1")),
        SupplyUnit.CENTIMETER: ("length", Decimal("10")),
        SupplyUnit.METER: ("length", Decimal("1000")),
        SupplyUnit.SQUARE_METER: ("area", Decimal("1")),
        SupplyUnit.CUBIC_METER: ("volume3", Decimal("1")),
    }

    @classmethod
    def convert(
        cls, quantity: Decimal, source: SupplyUnit, target: SupplyUnit
    ) -> Decimal:
        source_dimension, source_factor = cls._factors[source]
        target_dimension, target_factor = cls._factors[target]
        if source_dimension != target_dimension:
            raise UnitConversionError(
                f"No se puede convertir {source.value} a {target.value}"
            )
        return quantity * source_factor / target_factor
