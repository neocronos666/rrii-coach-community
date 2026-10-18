from decimal import Decimal
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.validation import (
    CountryCode,
    CurrencyCode,
    NonNegativeMoney,
    validate_iana_timezone,
)


class DepositPolicy(StrEnum):
    NONE = "none"
    OPTIONAL = "optional"
    REQUIRED = "required"


class DepositType(StrEnum):
    FIXED = "fixed"
    PERCENTAGE = "percentage"


class InstallationSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_name: str | None = Field(default=None, max_length=255)
    currency: CurrencyCode = "ARS"
    country_code: CountryCode = "AR"
    region: str | None = Field(default=None, max_length=255)
    timezone: str = "America/Argentina/Buenos_Aires"
    language: str = Field(default="es", pattern=r"^[a-z]{2,3}$")
    deposit_policy: DepositPolicy = DepositPolicy.NONE
    deposit_type: DepositType | None = None
    deposit_value: NonNegativeMoney | None = None
    electricity_price_per_kwh: NonNegativeMoney | None = None
    design_hour_rate: NonNegativeMoney | None = None
    preproduction_hour_rate: NonNegativeMoney | None = None
    postproduction_hour_rate: NonNegativeMoney | None = None
    assembly_hour_rate: NonNegativeMoney | None = None
    support_hour_rate: NonNegativeMoney | None = None
    training_hour_rate: NonNegativeMoney | None = None
    pretransport_hour_rate: NonNegativeMoney | None = None
    default_markup_percentage: NonNegativeMoney | None = None

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        return validate_iana_timezone(value)

    @model_validator(mode="after")
    def validate_deposit(self) -> Self:
        if self.deposit_policy is DepositPolicy.NONE:
            if self.deposit_type is not None or self.deposit_value is not None:
                raise ValueError("Una política de seña none no admite tipo ni valor")
            return self

        if self.deposit_type is None or self.deposit_value is None:
            raise ValueError("La política de seña requiere tipo y valor")
        if self.deposit_type is DepositType.PERCENTAGE and self.deposit_value > Decimal(
            100
        ):
            raise ValueError("El porcentaje de seña debe estar entre 0 y 100")
        return self


class InstallationSettingsUpdate(InstallationSettings):
    """Reemplazo completo de la configuración funcional."""
