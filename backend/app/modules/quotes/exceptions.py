class QuoteNotFoundError(Exception):
    pass


class QuoteNotEditableError(Exception):
    pass


class InvalidQuoteTransitionError(Exception):
    pass


class IncompleteCostCalculationError(Exception):
    pass


class MultiCurrencyQuoteUnsupportedError(Exception):
    pass


class InvalidDepositError(Exception):
    pass


class InvalidQuoteAdjustmentError(Exception):
    pass


class QuoteNotConvertibleError(Exception):
    pass
