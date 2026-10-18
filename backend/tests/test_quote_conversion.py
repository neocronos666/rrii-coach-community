import pytest

from app.modules.quotes.conversion_schemas import ConversionTargetType
from app.modules.quotes.conversion_service import target_type_for_item_count
from app.modules.quotes.exceptions import QuoteNotConvertibleError


def test_target_type_is_derived_only_from_item_count() -> None:
    assert target_type_for_item_count(1) is ConversionTargetType.ORDER
    assert target_type_for_item_count(2) is ConversionTargetType.PROJECT
    assert target_type_for_item_count(20) is ConversionTargetType.PROJECT


def test_quote_without_items_is_not_convertible() -> None:
    with pytest.raises(QuoteNotConvertibleError):
        target_type_for_item_count(0)
