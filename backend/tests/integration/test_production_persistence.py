from collections.abc import Iterator
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import SessionFactory
from app.main import app
from app.modules.production.models import ProductionTask
from tests.integration.test_hito7_conversion_api import approve, create_quote

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def clean_tasks() -> Iterator[None]:
    with SessionFactory() as session:
        session.execute(delete(ProductionTask))
        session.commit()
    yield
    with SessionFactory() as session:
        session.execute(delete(ProductionTask))
        session.commit()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def create_order_id(client: TestClient) -> UUID:
    quote = create_quote(client, ["100"])
    approve(client, quote["id"])
    response = client.post(f"/api/v1/quotes/{quote['id']}/convert")
    return UUID(response.json()["target_id"])


def create_component_id(client: TestClient) -> UUID:
    quote = create_quote(client, ["100", "200"])
    approve(client, quote["id"])
    response = client.post(f"/api/v1/quotes/{quote['id']}/convert")
    project = client.get(f"/api/v1/projects/{response.json()['target_id']}").json()
    return UUID(project["components"][0]["id"])


def task(**changes: object) -> ProductionTask:
    values: dict[str, object] = {
        "code": f"T-2026-{uuid4().int % 1_000_000:06d}",
        "execution_mode": "legacy",
        "task_type": "manual",
        "title": "Tarea de persistencia",
        "planned_quantity": Decimal("2.500000"),
        "queue_position": 10,
    }
    values.update(changes)
    return ProductionTask(**values)


def persist(session: Session, value: ProductionTask) -> ProductionTask:
    session.add(value)
    session.commit()
    session.refresh(value)
    return value


def test_order_origin_decimal_jsonb_and_defaults(client: TestClient) -> None:
    with SessionFactory() as session:
        value = persist(
            session,
            task(
                order_id=create_order_id(client),
                production_parameters={
                    "layer_height_mm": "0.20",
                    "infill_percentage": "20",
                },
            ),
        )
        assert value.order_id is not None
        assert value.project_component_id is None
        assert value.planned_quantity == Decimal("2.500000")
        assert value.production_parameters["layer_height_mm"] == "0.20"
        assert value.status == "queued"
        assert value.priority == "normal"


def test_project_component_origin(client: TestClient) -> None:
    with SessionFactory() as session:
        value = persist(session, task(project_component_id=create_component_id(client)))
        assert value.order_id is None
        assert value.project_component_id is not None


@pytest.mark.parametrize("quantity", [Decimal("0"), Decimal("-1")])
def test_nonpositive_quantity_is_rejected(
    client: TestClient, quantity: Decimal
) -> None:
    with SessionFactory() as session:
        session.add(task(order_id=create_order_id(client), planned_quantity=quantity))
        with pytest.raises(IntegrityError):
            session.commit()


def test_null_and_double_origins_are_rejected(client: TestClient) -> None:
    order_id = create_order_id(client)
    component_id = create_component_id(client)
    for value in (task(), task(order_id=order_id, project_component_id=component_id)):
        with SessionFactory() as session:
            session.add(value)
            with pytest.raises(IntegrityError):
                session.commit()


def test_foreign_keys_are_enforced(client: TestClient) -> None:
    with SessionFactory() as session:
        session.add(task(order_id=create_order_id(client), machine_id=uuid4()))
        with pytest.raises(IntegrityError):
            session.commit()
