class SupplyNotFoundError(RuntimeError):
    """No existe el insumo solicitado."""


class PresentationNotFoundError(RuntimeError):
    """No existe la presentación solicitada para el insumo."""


class InsufficientStockError(RuntimeError):
    """La salida solicitada superaría la existencia disponible."""


class BaseUnitLockedError(RuntimeError):
    """La unidad base no puede cambiar luego del primer movimiento."""


class UnitConversionError(ValueError):
    """Las unidades no pertenecen a la misma dimensión convertible."""


class EstimatedCostUnavailableError(RuntimeError):
    """El insumo no posee compras válidas para estimar un costo."""


class DuplicateSupplySkuError(RuntimeError):
    """El SKU indicado ya pertenece a otro insumo."""
