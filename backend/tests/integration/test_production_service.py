from collections.abc import Iterator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionFactory
from app.main import app
from app.modules.machines.models import Machine
from app.modules.orders.models import Order
from app.modules.production.exceptions import InactiveMachineError, MachineBusyError
from app.modules.production.models import ProductionTask
from app.modules.production.service import ProductionTaskService
from app.modules.supplies.models import SupplyStockMovement
from tests.integration.test_production_persistence import create_order_id, task

pytestmark = pytest.mark.integration


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as value:
        yield value


def machine(*, active: bool = True) -> Machine:
    return Machine(
        name=f"Machine {uuid4()}",
        machine_type="other",
        currency="ARS",
        active=active,
    )


def seed(client: TestClient, machine_id: UUID | None = None) -> ProductionTask:
    with SessionFactory() as session:
        value = task(order_id=create_order_id(client), machine_id=machine_id)
        session.add(value)
        session.commit()
        session.refresh(value)
        session.expunge(value)
        return value


def test_machine_busy_pause_release_and_resume_blocked(client: TestClient) -> None:
    with SessionFactory() as session:
        resource = machine()
        session.add(resource)
        session.commit()
        machine_id = resource.id
    first = seed(client, machine_id)
    second = seed(client, machine_id)
    with SessionFactory() as session:
        service = ProductionTaskService(session)
        service.start(first.id)
        with pytest.raises(MachineBusyError):
            service.start(second.id)
        service.pause(first.id)
        service.start(second.id)
        with pytest.raises(MachineBusyError):
            service.resume(first.id)


def test_database_partial_unique_index_is_authoritative(client: TestClient) -> None:
    with SessionFactory() as session:
        resource = machine()
        session.add(resource)
        session.commit()
        one = task(
            order_id=create_order_id(client),
            machine_id=resource.id,
            status="in_progress",
        )
        two = task(
            order_id=create_order_id(client),
            machine_id=resource.id,
            status="in_progress",
        )
        session.add_all([one, two])
        with pytest.raises(IntegrityError):
            session.commit()


def test_parallel_machines_and_manual_tasks(client: TestClient) -> None:
    with SessionFactory() as session:
        first_machine, second_machine = machine(), machine()
        session.add_all([first_machine, second_machine])
        session.commit()
        ids = (first_machine.id, second_machine.id)
    values = [seed(client, ids[0]), seed(client, ids[1]), seed(client), seed(client)]
    with SessionFactory() as session:
        service = ProductionTaskService(session)
        for value in values:
            assert service.start(value.id).status == "in_progress"


def test_inactive_machine_assignment_start_and_resume(client: TestClient) -> None:
    with SessionFactory() as session:
        inactive, active, resume_machine = machine(active=False), machine(), machine()
        session.add_all([inactive, active, resume_machine])
        session.commit()
        inactive_id, active_id, resume_machine_id = (
            inactive.id,
            active.id,
            resume_machine.id,
        )
    queued = seed(client)
    with SessionFactory() as session:
        service = ProductionTaskService(session)
        with pytest.raises(InactiveMachineError):
            service.update(queued.id, {"machine_id": inactive_id})
        service.update(queued.id, {"machine_id": active_id})
        current_machine = session.get(Machine, active_id)
        assert current_machine is not None
        current_machine.active = False
        session.commit()
        with pytest.raises(InactiveMachineError):
            service.start(queued.id)
    paused = seed(client)
    with SessionFactory() as session:
        service = ProductionTaskService(session)
        service.update(paused.id, {"machine_id": resume_machine_id})
        service.start(paused.id)
        service.pause(paused.id)
        current_machine = session.get(Machine, resume_machine_id)
        assert current_machine is not None
        current_machine.active = False
        session.commit()
        with pytest.raises(InactiveMachineError):
            service.resume(paused.id)


def test_finish_changes_neither_stock_nor_order(client: TestClient) -> None:
    value = seed(client)
    with SessionFactory() as session:
        before = session.scalar(select(func.count()).select_from(SupplyStockMovement))
        order = session.get(Order, value.order_id)
        assert order is not None
        order_status = order.status
        service = ProductionTaskService(session)
        service.start(value.id)
        service.pause(value.id)
        service.resume(value.id)
        finished = service.finish(value.id)
        assert finished.physically_completed_at is not None
        assert (
            session.scalar(select(func.count()).select_from(SupplyStockMovement))
            == before
        )
        order = session.get(Order, value.order_id)
        assert order is not None
        assert order.status == order_status
