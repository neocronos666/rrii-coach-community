import logging
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.community import CommunityLimits
from app.db.exceptions import PersistenceError
from app.modules.installation.service import InstallationSettingsService
from app.modules.machines.exceptions import (
    CommunityMachineLimitError,
    MachineNotFoundError,
)
from app.modules.machines.models import Machine
from app.modules.machines.repository import MachineRepository
from app.modules.machines.schemas import MachineCreate, MachineType, MachineUpdate

logger = logging.getLogger(__name__)


class MachineService:
    def __init__(
        self,
        session: Session,
        repository: MachineRepository | None = None,
        installation_settings: InstallationSettingsService | None = None,
    ) -> None:
        self._session = session
        self._repository = repository or MachineRepository(session)
        self._installation_settings = installation_settings or (
            InstallationSettingsService(session)
        )

    def list(
        self,
        *,
        active: bool | None = None,
        machine_type: MachineType | None = None,
    ) -> list[Machine]:
        return self._repository.list(active=active, machine_type=machine_type)

    def get(self, machine_id: UUID) -> Machine:
        machine = self._repository.get(machine_id)
        if machine is None:
            raise MachineNotFoundError("No existe la máquina solicitada")
        return machine

    def create(self, payload: MachineCreate) -> Machine:
        try:
            if payload.active:
                self._enforce_active_limit()
            currency = payload.currency or self._installation_settings.get().currency
            data = payload.model_dump(exclude={"currency", "machine_type"})
            machine = Machine(
                **data,
                machine_type=payload.machine_type.value,
                currency=currency,
            )
            self._repository.add(machine)
            self._session.commit()
            logger.info("machine_created machine_id=%s", machine.id)
            return machine
        except CommunityMachineLimitError:
            self._session.rollback()
            raise
        except SQLAlchemyError as error:
            self._rollback(error)
            raise PersistenceError("No se pudo crear la máquina") from error

    def update(self, machine_id: UUID, payload: MachineUpdate) -> Machine:
        try:
            machine = self.get(machine_id)
            changes = payload.model_dump(exclude_unset=True)
            requested_active = changes.get("active")
            if requested_active is True and not machine.active:
                self._enforce_active_limit()
            machine_type = changes.get("machine_type")
            if isinstance(machine_type, MachineType):
                changes["machine_type"] = machine_type.value

            was_active = machine.active
            self._repository.update(machine, changes)
            self._session.commit()
            logger.info("machine_updated machine_id=%s", machine.id)
            if was_active and not machine.active:
                logger.info("machine_deactivated machine_id=%s", machine.id)
            elif not was_active and machine.active:
                logger.info("machine_reactivated machine_id=%s", machine.id)
            return machine
        except (MachineNotFoundError, CommunityMachineLimitError):
            self._session.rollback()
            raise
        except SQLAlchemyError as error:
            self._rollback(error)
            raise PersistenceError("No se pudo actualizar la máquina") from error

    def _enforce_active_limit(self) -> None:
        if self._repository.count_active() >= CommunityLimits.MAX_ACTIVE_MACHINES:
            logger.warning("community_machine_limit_reached")
            raise CommunityMachineLimitError(
                "Community admite hasta dos máquinas activas"
            )

    def _rollback(self, error: SQLAlchemyError) -> None:
        self._session.rollback()
        logger.error(
            "machine_transaction_failed (%s); rollback ejecutado",
            type(error).__name__,
        )
