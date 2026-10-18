from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.repositories import SystemSettingsRepository
from app.modules.installation.schemas import (
    DepositPolicy,
    DepositType,
    InstallationSettings,
    InstallationSettingsUpdate,
)
from app.modules.installation.service import InstallationSettingsService


def test_installation_settings_defaults() -> None:
    settings = InstallationSettings()

    assert settings.business_name is None
    assert settings.currency == "ARS"
    assert settings.country_code == "AR"
    assert settings.timezone == "America/Argentina/Buenos_Aires"
    assert settings.language == "es"
    assert settings.deposit_policy is DepositPolicy.NONE
    assert settings.electricity_price_per_kwh is None
    assert settings.design_hour_rate is None


def test_economic_rates_distinguish_missing_from_zero() -> None:
    settings = InstallationSettings(postproduction_hour_rate=Decimal("0"))

    assert settings.postproduction_hour_rate == Decimal("0")
    assert settings.preproduction_hour_rate is None


@pytest.mark.parametrize("currency", ["ars", "AR", "PESO"])
def test_installation_settings_reject_invalid_currency(currency: str) -> None:
    with pytest.raises(ValidationError):
        InstallationSettings(currency=currency)


def test_installation_settings_reject_invalid_timezone() -> None:
    with pytest.raises(ValidationError, match="IANA"):
        InstallationSettings(timezone="-03:00")


def test_installation_settings_validate_percentage_deposit() -> None:
    settings = InstallationSettings(
        deposit_policy=DepositPolicy.REQUIRED,
        deposit_type=DepositType.PERCENTAGE,
        deposit_value=Decimal("50"),
    )

    assert settings.deposit_value == Decimal("50")

    with pytest.raises(ValidationError, match="entre 0 y 100"):
        InstallationSettings(
            deposit_policy=DepositPolicy.REQUIRED,
            deposit_type=DepositType.PERCENTAGE,
            deposit_value=Decimal("101"),
        )


def test_installation_settings_none_rejects_value() -> None:
    with pytest.raises(ValidationError, match="no admite"):
        InstallationSettings(
            deposit_policy=DepositPolicy.NONE,
            deposit_type=DepositType.FIXED,
            deposit_value=Decimal("0"),
        )


def test_installation_service_updates_through_typed_interface() -> None:
    session = MagicMock(spec=Session)
    repository = MagicMock(spec=SystemSettingsRepository)
    repository.get_by_key.return_value = None
    service = InstallationSettingsService(session, repository)
    payload = InstallationSettingsUpdate(
        business_name="Taller de prueba",
        currency="USD",
    )

    result = service.update(payload)

    assert result.business_name == "Taller de prueba"
    assert result.currency == "USD"
    repository.create.assert_called_once()
    session.commit.assert_called_once_with()
