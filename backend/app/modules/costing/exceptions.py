class CurrencyMismatchError(ValueError):
    """La operación intentó mezclar monedas diferentes."""


class CostCalculationNotFoundError(RuntimeError):
    """No existe el cálculo histórico solicitado."""
