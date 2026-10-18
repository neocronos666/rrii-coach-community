import logging
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError, SettingNotFoundError
from app.db.models import SystemSetting
from app.db.repositories import SystemSettingsRepository

logger = logging.getLogger(__name__)


class SystemSettingsService:
    """Frontera transaccional para configuraciones técnicas no sensibles."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repository = SystemSettingsRepository(session)

    def create(self, *, key: str, value: dict[str, Any]) -> SystemSetting:
        try:
            setting = self._repository.create(key=key, value=value)
            self._session.commit()
            return setting
        except SQLAlchemyError as error:
            self._rollback(error)
            raise PersistenceError("No se pudo guardar la configuración") from error

    def update(self, *, key: str, value: dict[str, Any]) -> SystemSetting:
        try:
            setting = self._repository.get_by_key(key)
            if setting is None:
                raise SettingNotFoundError(
                    "No existe la configuración técnica solicitada"
                )
            self._repository.update(setting, value=value)
            self._session.commit()
            return setting
        except SettingNotFoundError:
            self._session.rollback()
            raise
        except SQLAlchemyError as error:
            self._rollback(error)
            raise PersistenceError("No se pudo actualizar la configuración") from error

    def _rollback(self, error: SQLAlchemyError) -> None:
        self._session.rollback()
        logger.error(
            "Error transaccional de persistencia (%s); se ejecutó rollback",
            type(error).__name__,
        )
