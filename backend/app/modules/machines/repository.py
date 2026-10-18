from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.machines.models import Machine
from app.modules.machines.schemas import MachineType


class MachineRepository:
    """Persistencia específica de máquinas, sin frontera transaccional."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, machine: Machine) -> Machine:
        self._session.add(machine)
        self._session.flush()
        return machine

    def get(self, machine_id: UUID) -> Machine | None:
        return self._session.get(Machine, machine_id)

    def list(
        self,
        *,
        active: bool | None = None,
        machine_type: MachineType | None = None,
    ) -> list[Machine]:
        statement = select(Machine).order_by(Machine.created_at, Machine.id)
        if active is not None:
            statement = statement.where(Machine.active.is_(active))
        if machine_type is not None:
            statement = statement.where(Machine.machine_type == machine_type.value)
        return list(self._session.scalars(statement))

    def count_active(self) -> int:
        statement = select(func.count()).select_from(Machine).where(Machine.active)
        return self._session.scalar(statement) or 0

    def update(self, machine: Machine, changes: dict[str, object]) -> Machine:
        for field_name, value in changes.items():
            setattr(machine, field_name, value)
        self._session.flush()
        return machine
