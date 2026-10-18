from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.db.session import get_db_session
from app.modules.installation.exceptions import InstallationSettingsCorruptedError
from app.modules.installation.schemas import (
    InstallationSettings,
    InstallationSettingsUpdate,
)
from app.modules.installation.service import InstallationSettingsService

router = APIRouter(prefix="/settings", tags=["settings"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]


@router.get(
    "",
    response_model=InstallationSettings,
    summary="Obtener configuración Community",
    description="Devuelve la configuración funcional activa o sus valores iniciales.",
)
def get_installation_settings(session: DatabaseSession) -> InstallationSettings:
    try:
        return InstallationSettingsService(session).get()
    except InstallationSettingsCorruptedError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="La configuración persistida no es válida",
        ) from error


@router.put(
    "",
    response_model=InstallationSettings,
    summary="Actualizar configuración Community",
    description="Reemplaza la configuración funcional completa de la instalación.",
)
def update_installation_settings(
    payload: InstallationSettingsUpdate,
    session: DatabaseSession,
) -> InstallationSettings:
    try:
        return InstallationSettingsService(session).update(payload)
    except PersistenceError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo guardar la configuración",
        ) from error
