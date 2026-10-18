import logging

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.db.repositories import SystemSettingsRepository
from app.modules.installation.exceptions import InstallationSettingsCorruptedError
from app.modules.installation.schemas import (
    InstallationSettings,
    InstallationSettingsUpdate,
)

logger = logging.getLogger(__name__)
INSTALLATION_SETTINGS_KEY = "community.installation_settings"


class InstallationSettingsService:
    """Interfaz tipada sobre el almacenamiento técnico clave/valor."""

    def __init__(
        self,
        session: Session,
        repository: SystemSettingsRepository | None = None,
    ) -> None:
        self._session = session
        self._repository = repository or SystemSettingsRepository(session)

    def get(self) -> InstallationSettings:
        setting = self._repository.get_by_key(INSTALLATION_SETTINGS_KEY)
        if setting is None:
            return InstallationSettings()
        try:
            return InstallationSettings.model_validate(setting.value)
        except ValidationError as error:
            raise InstallationSettingsCorruptedError(
                "La configuración persistida no es válida"
            ) from error

    def update(self, settings: InstallationSettingsUpdate) -> InstallationSettings:
        payload = settings.model_dump(mode="json")
        try:
            current = self._repository.get_by_key(INSTALLATION_SETTINGS_KEY)
            if current is None:
                self._repository.create(
                    key=INSTALLATION_SETTINGS_KEY,
                    value=payload,
                )
            else:
                self._repository.update(current, value=payload)
            self._session.commit()
            logger.info("installation_settings_updated")
            return InstallationSettings.model_validate(payload)
        except SQLAlchemyError as error:
            self._session.rollback()
            logger.error(
                "installation_settings_update_failed (%s); rollback ejecutado",
                type(error).__name__,
            )
            raise PersistenceError(
                "No se pudo actualizar la configuración de instalación"
            ) from error
