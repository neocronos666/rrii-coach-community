from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import SystemSetting


class SystemSettingsRepository:
    """Acceso mínimo a configuraciones técnicas; nunca confirma transacciones."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, *, key: str, value: dict[str, Any]) -> SystemSetting:
        setting = SystemSetting(key=key, value=value)
        self._session.add(setting)
        self._session.flush()
        return setting

    def get_by_key(self, key: str) -> SystemSetting | None:
        statement = select(SystemSetting).where(SystemSetting.key == key)
        return self._session.scalar(statement)

    def update(
        self,
        setting: SystemSetting,
        *,
        value: dict[str, Any],
    ) -> SystemSetting:
        setting.value = value
        self._session.flush()
        return setting

    def list(self) -> list[SystemSetting]:
        statement = select(SystemSetting).order_by(SystemSetting.key)
        return list(self._session.scalars(statement))
