from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.modules.installation.schemas import InstallationSettings
from app.modules.installation.service import InstallationSettingsService
from app.modules.machines.exceptions import CommunityMachineLimitError
from app.modules.machines.models import Machine
from app.modules.machines.repository import MachineRepository
from app.modules.machines.schemas import MachineCreate, MachineType, MachineUpdate
from app.modules.machines.service import MachineService


def build_service(
    *,
    active_count: int = 0,
) -> tuple[MachineService, MagicMock, MagicMock]:
    session = MagicMock(spec=Session)
    repository = MagicMock(spec=MachineRepository)
    repository.count_active.return_value = active_count
    installation = MagicMock(spec=InstallationSettingsService)
    installation.get.return_value = InstallationSettings(currency="ARS")
    service = MachineService(session, repository, installation)
    return service, repository, session


def machine(*, active: bool = True) -> Machine:
    return Machine(
        id=uuid4(),
        name="Máquina de prueba",
        machine_type=MachineType.FDM_PRINTER.value,
        currency="ARS",
        active=active,
    )


def apply_changes(value: Machine, changes: dict[str, object]) -> Machine:
    for key, item in changes.items():
        setattr(value, key, item)
    return value


def test_machine_create_uses_decimal_and_defaults() -> None:
    payload = MachineCreate(
        name="CNC chica",
        machine_type=MachineType.CNC,
        purchase_date=date(2026, 8, 14),
        purchase_price=Decimal("1234.5678"),
    )

    assert payload.purchase_price == Decimal("1234.5678")
    assert payload.active is True


def test_machine_rejects_float_like_excess_precision() -> None:
    with pytest.raises(ValidationError):
        MachineCreate(
            name="Láser",
            machine_type=MachineType.LASER,
            purchase_price=Decimal("1.00001"),
        )


@pytest.mark.parametrize("active_count", [0, 1])
def test_create_active_machine_below_limit(active_count: int) -> None:
    service, repository, session = build_service(active_count=active_count)
    repository.add.side_effect = lambda value: value

    created = service.create(
        MachineCreate(name="Equipo", machine_type=MachineType.OTHER)
    )

    assert created.active is True
    assert created.currency == "ARS"
    session.commit.assert_called_once_with()


def test_create_third_active_machine_is_rejected() -> None:
    service, repository, session = build_service(active_count=2)

    with pytest.raises(CommunityMachineLimitError):
        service.create(MachineCreate(name="Tercera", machine_type=MachineType.CNC))

    repository.add.assert_not_called()
    session.rollback.assert_called_once_with()


def test_edit_active_machine_at_limit_is_allowed() -> None:
    service, repository, session = build_service(active_count=2)
    current = machine(active=True)
    repository.get.return_value = current
    repository.update.side_effect = apply_changes

    updated = service.update(current.id, MachineUpdate(name="Nombre nuevo"))

    assert updated.name == "Nombre nuevo"
    repository.count_active.assert_not_called()
    session.commit.assert_called_once_with()


def test_deactivate_machine_at_limit_is_allowed() -> None:
    service, repository, _ = build_service(active_count=2)
    current = machine(active=True)
    repository.get.return_value = current
    repository.update.side_effect = apply_changes

    updated = service.update(current.id, MachineUpdate(active=False))

    assert updated.active is False
    repository.count_active.assert_not_called()


def test_reactivate_machine_below_limit_is_allowed() -> None:
    service, repository, session = build_service(active_count=1)
    current = machine(active=False)
    repository.get.return_value = current
    repository.update.side_effect = apply_changes

    updated = service.update(current.id, MachineUpdate(active=True))

    assert updated.active is True
    repository.count_active.assert_called_once_with()
    session.commit.assert_called_once_with()


def test_reactivate_machine_at_limit_is_rejected() -> None:
    service, repository, session = build_service(active_count=2)
    current = machine(active=False)
    repository.get.return_value = current

    with pytest.raises(CommunityMachineLimitError):
        service.update(current.id, MachineUpdate(active=True))

    repository.update.assert_not_called()
    session.rollback.assert_called_once_with()
