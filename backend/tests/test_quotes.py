from decimal import Decimal

import pytest

from app.modules.installation.schemas import DepositPolicy, DepositType
from app.modules.quotes.calculator import QuoteCalculator
from app.modules.quotes.exceptions import (
    InvalidDepositError,
    InvalidQuoteAdjustmentError,
)
from app.modules.quotes.types import AdjustmentSpec, AdjustmentType, AdjustmentValueType


def adjustment(
    kind: AdjustmentType, value_type: AdjustmentValueType, value: str
) -> AdjustmentSpec:
    return AdjustmentSpec("Ajuste", kind, value_type, Decimal(value))


def test_markup_and_percentage_surcharge() -> None:
    result = QuoteCalculator().calculate(
        Decimal("1000"),
        Decimal("50"),
        [adjustment(AdjustmentType.SURCHARGE, AdjustmentValueType.PERCENTAGE, "20")],
    )
    assert result.markup_amount == Decimal("500.0000")
    assert result.subtotal_after_markup == Decimal("1500.0000")
    assert result.adjustments[0].amount == Decimal("300.0000")
    assert result.suggested_price == Decimal("1800.0000")


def test_no_markup_discount_and_fixed_adjustments() -> None:
    result = QuoteCalculator().calculate(
        Decimal("1000"),
        Decimal("0"),
        [
            adjustment(AdjustmentType.DISCOUNT, AdjustmentValueType.PERCENTAGE, "10"),
            adjustment(AdjustmentType.SURCHARGE, AdjustmentValueType.FIXED, "50"),
            adjustment(AdjustmentType.DISCOUNT, AdjustmentValueType.FIXED, "25"),
        ],
    )
    assert result.suggested_price == Decimal("925.0000")


def test_all_percentages_use_original_post_markup_subtotal() -> None:
    result = QuoteCalculator().calculate(
        Decimal("1000"),
        Decimal("50"),
        [
            adjustment(AdjustmentType.SURCHARGE, AdjustmentValueType.PERCENTAGE, "20"),
            adjustment(AdjustmentType.DISCOUNT, AdjustmentValueType.PERCENTAGE, "10"),
        ],
    )
    assert [item.amount for item in result.adjustments] == [
        Decimal("300.0000"),
        Decimal("150.0000"),
    ]
    assert result.suggested_price == Decimal("1650.0000")


def test_adjustment_cannot_make_price_negative() -> None:
    with pytest.raises(InvalidQuoteAdjustmentError):
        QuoteCalculator().calculate(
            Decimal("1000"),
            Decimal("0"),
            [adjustment(AdjustmentType.DISCOUNT, AdjustmentValueType.FIXED, "1001")],
        )


def test_percentage_and_fixed_deposits() -> None:
    calculator = QuoteCalculator()
    assert calculator.calculate_deposit(
        Decimal("100000"), DepositPolicy.REQUIRED, DepositType.PERCENTAGE, Decimal("50")
    ) == Decimal("50000.0000")
    assert calculator.calculate_deposit(
        Decimal("100000"), DepositPolicy.OPTIONAL, DepositType.FIXED, Decimal("20000")
    ) == Decimal("20000.0000")
    assert (
        calculator.calculate_deposit(Decimal("100000"), DepositPolicy.NONE, None, None)
        is None
    )


def test_fixed_deposit_cannot_exceed_final_price() -> None:
    with pytest.raises(InvalidDepositError):
        QuoteCalculator().calculate_deposit(
            Decimal("1000"), DepositPolicy.REQUIRED, DepositType.FIXED, Decimal("1001")
        )


@pytest.mark.parametrize(
    "amount", ["0", "0.9999", "1", "1.9999", "1234.87", "99999999999999.9999"]
)
def test_ars_final_price_never_increases_and_is_idempotent(amount: str) -> None:
    original = Decimal(amount)
    calculator = QuoteCalculator()
    rounded = calculator.round_final_price(original, "ARS")
    assert rounded <= original < rounded + 1
    assert rounded == rounded.to_integral_value()
    assert calculator.round_final_price(rounded, "ARS") == rounded
    assert calculator.round_final_price(original, "USD") == original
