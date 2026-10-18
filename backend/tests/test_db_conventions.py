from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import DateTime

from app.db.base import Base
from app.db.models import SystemSetting


def test_system_setting_uses_expected_constraint_names() -> None:
    table = Base.metadata.tables["system_settings"]

    assert table.primary_key.name == "pk_system_settings"
    assert {constraint.name for constraint in table.constraints} >= {
        "pk_system_settings",
        "uq_system_settings_key",
    }


def test_system_setting_declares_uuid_and_timezone_aware_timestamps() -> None:
    table = SystemSetting.__table__
    created_at_type = cast(DateTime, table.c.created_at.type)
    updated_at_type = cast(DateTime, table.c.updated_at.type)

    assert table.c.id.type.python_type is UUID
    assert created_at_type.python_type is datetime
    assert created_at_type.timezone is True
    assert updated_at_type.timezone is True
