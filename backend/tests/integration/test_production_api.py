import re
from collections.abc import Iterator
from decimal import Decimal
from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.db.session import SessionFactory
from app.main import app
from app.modules.machines.models import Machine
from app.modules.orders.models import Order
from app.modules.production.models import ProductionTask, ProductionTaskDependency
from app.modules.projects.models import Project
from app.modules.supplies.models import SupplyStockMovement
from tests.integration.test_hito7_conversion_api import (
    approve,
    clean,
    create_quote,
)

pytestmark = pytest.mark.integration
MISSING_ID = "00000000-0000-0000-0000-000000000000"


def clean_data() -> None:
    with SessionFactory() as session:
        session.execute(delete(ProductionTaskDependency))
        session.execute(delete(ProductionTask))
        clean(session)
        session.execute(delete(Machine))
        session.commit()


@pytest.fixture(autouse=True)
def clean_production_api_data() -> Iterator[None]:
    clean_data()
    yield
    clean_data()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def create_order(client: TestClient) -> str:
    quote = create_quote(client, ["100"])
    approve(client, quote["id"])
    response = client.post(f"/api/v1/quotes/{quote['id']}/convert")
    assert response.status_code == 201
    return str(response.json()["target_id"])


def create_project(client: TestClient) -> tuple[str, str]:
    quote = create_quote(client, ["100", "200"])
    approve(client, quote["id"])
    converted = client.post(f"/api/v1/quotes/{quote['id']}/convert")
    assert converted.status_code == 201
    project_id = str(converted.json()["target_id"])
    project = client.get(f"/api/v1/projects/{project_id}").json()
    return project_id, str(project["components"][0]["id"])


def create_machine(client: TestClient, *, active: bool = True) -> str:
    response = client.post(
        "/api/v1/machines",
        json={
            "name": f"Machine {uuid4()}",
            "machine_type": "other",
            "active": active,
        },
    )
    assert response.status_code == 201
    return str(response.json()["id"])


def task_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "task_type": "manual",
        "title": "Preparar pieza",
        "planned_quantity": "2.5",
        "queue_position": 20,
    }
    payload.update(overrides)
    return payload


def mark_legacy(task_id: str) -> None:
    """Simula un registro anterior a Hito 9 para verificar compatibilidad."""
    with SessionFactory() as session:
        task = session.get(ProductionTask, UUID(task_id))
        assert task is not None
        task.execution_mode = "legacy"
        session.commit()


def create_task(
    client: TestClient, order_id: str, **overrides: object
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/orders/{order_id}/production-tasks",
        json=task_payload(**overrides),
    )
    assert response.status_code == 201, response.text
    mark_legacy(str(response.json()["id"]))
    return cast(dict[str, object], response.json())


def test_create_from_order_is_parent_scoped_and_uses_defaults(
    client: TestClient,
) -> None:
    order_id = create_order(client)
    response = client.post(
        f"/api/v1/orders/{order_id}/production-tasks",
        json={
            "task_type": "fdm_print",
            "title": "Imprimir",
            "planned_quantity": "2.5",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["order_id"] == order_id
    assert body["project_component_id"] is None
    assert re.fullmatch(r"T-\d{4}-\d{6}", body["code"])
    assert body["status"] == "queued"
    assert body["priority"] == "normal"
    assert body["queue_position"] == 1000
    assert body["production_parameters"] == {}
    assert Decimal(body["planned_quantity"]) == Decimal("2.5")
    invalid = client.post(
        f"/api/v1/orders/{order_id}/production-tasks",
        json={**task_payload(), "status": "in_progress", "order_id": order_id},
    )
    assert invalid.status_code == 422


def test_create_from_project_component_and_cancelled_origins(
    client: TestClient,
) -> None:
    project_id, component_id = create_project(client)
    created = client.post(
        f"/api/v1/project-components/{component_id}/production-tasks",
        json=task_payload(task_type="assembly"),
    )
    assert created.status_code == 201
    assert created.json()["order_id"] is None
    assert created.json()["project_component_id"] == component_id

    assert client.post(f"/api/v1/projects/{project_id}/cancel").status_code == 200
    blocked = client.post(
        f"/api/v1/project-components/{component_id}/production-tasks",
        json=task_payload(),
    )
    assert blocked.status_code == 409

    order_id = create_order(client)
    assert client.post(f"/api/v1/orders/{order_id}/cancel").status_code == 200
    assert (
        client.post(
            f"/api/v1/orders/{order_id}/production-tasks", json=task_payload()
        ).status_code
        == 409
    )


def test_missing_origins_return_not_found(client: TestClient) -> None:
    assert (
        client.post(
            f"/api/v1/orders/{MISSING_ID}/production-tasks", json=task_payload()
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/project-components/{MISSING_ID}/production-tasks",
            json=task_payload(),
        ).status_code
        == 404
    )


def test_machine_validation_on_create(client: TestClient) -> None:
    order_id = create_order(client)
    inactive_id = create_machine(client, active=False)
    active_id = create_machine(client)

    assert create_task(client, order_id)["machine_id"] is None
    assert (
        create_task(client, order_id, machine_id=active_id)["machine_id"] == active_id
    )
    missing = client.post(
        f"/api/v1/orders/{order_id}/production-tasks",
        json=task_payload(machine_id=MISSING_ID),
    )
    assert missing.status_code == 404
    inactive = client.post(
        f"/api/v1/orders/{order_id}/production-tasks",
        json=task_payload(machine_id=inactive_id),
    )
    assert inactive.status_code == 409


def test_inactive_machine_blocks_start_and_resume(client: TestClient) -> None:
    order_id = create_order(client)
    start_machine = create_machine(client)
    start_task = create_task(client, order_id, machine_id=start_machine)
    assert (
        client.patch(
            f"/api/v1/machines/{start_machine}", json={"active": False}
        ).status_code
        == 200
    )
    assert (
        client.post(f"/api/v1/production-tasks/{start_task['id']}/start").status_code
        == 409
    )

    resume_machine = create_machine(client)
    resume_task = create_task(client, order_id, machine_id=resume_machine)
    assert (
        client.post(f"/api/v1/production-tasks/{resume_task['id']}/start").status_code
        == 200
    )
    assert (
        client.post(f"/api/v1/production-tasks/{resume_task['id']}/pause").status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/v1/machines/{resume_machine}", json={"active": False}
        ).status_code
        == 200
    )
    assert (
        client.post(f"/api/v1/production-tasks/{resume_task['id']}/resume").status_code
        == 409
    )


def test_list_order_filters_detail_and_project_filter(client: TestClient) -> None:
    order_id = create_order(client)
    machine_id = create_machine(client)
    low = create_task(client, order_id, title="Low", priority="low", queue_position=1)
    urgent_late = create_task(
        client,
        order_id,
        title="Urgent late",
        priority="urgent",
        queue_position=30,
        machine_id=machine_id,
    )
    urgent_early = create_task(
        client,
        order_id,
        title="Urgent early",
        priority="urgent",
        queue_position=10,
    )
    project_id, component_id = create_project(client)
    component_task = client.post(
        f"/api/v1/project-components/{component_id}/production-tasks",
        json=task_payload(priority="high"),
    ).json()

    listed = client.get("/api/v1/production-tasks").json()
    assert [item["id"] for item in listed] == [
        urgent_early["id"],
        urgent_late["id"],
        component_task["id"],
        low["id"],
    ]
    filters = {
        "priority=low": low["id"],
        f"machine_id={machine_id}": urgent_late["id"],
        f"order_id={order_id}&priority=low": low["id"],
        f"project_component_id={component_id}": component_task["id"],
        f"project_id={project_id}": component_task["id"],
    }
    for query, expected_id in filters.items():
        assert [
            item["id"]
            for item in client.get(f"/api/v1/production-tasks?{query}").json()
        ] == [expected_id]
    assert client.post(f"/api/v1/production-tasks/{low['id']}/start").status_code == 200
    assert [
        item["id"]
        for item in client.get("/api/v1/production-tasks?status=in_progress").json()
    ] == [low["id"]]
    assert client.get(f"/api/v1/production-tasks/{low['id']}").status_code == 200
    assert client.get(f"/api/v1/production-tasks/{MISSING_ID}").status_code == 404


def test_patch_is_partial_state_aware_and_accepts_explicit_null(
    client: TestClient,
) -> None:
    order_id = create_order(client)
    machine_id = create_machine(client)
    task = create_task(
        client,
        order_id,
        description="Temporal",
        notes="Temporal",
        machine_id=machine_id,
    )
    task_id = task["id"]
    queued = client.patch(
        f"/api/v1/production-tasks/{task_id}",
        json={
            "title": "Actualizada",
            "description": None,
            "priority": "high",
            "planned_quantity": "3.75",
            "machine_id": None,
            "queue_position": 10,
            "production_parameters": {"profile": "manual"},
            "notes": None,
        },
    )
    assert queued.status_code == 200
    assert queued.json()["description"] is None
    assert queued.json()["machine_id"] is None
    assert Decimal(queued.json()["planned_quantity"]) == Decimal("3.75")
    assert (
        client.patch(
            f"/api/v1/production-tasks/{task_id}", json={"status": "cancelled"}
        ).status_code
        == 422
    )

    assert client.post(f"/api/v1/production-tasks/{task_id}/start").status_code == 200
    allowed = client.patch(
        f"/api/v1/production-tasks/{task_id}",
        json={"notes": "En proceso", "production_parameters": {"rpm": "100"}},
    )
    assert allowed.status_code == 200
    assert (
        client.patch(
            f"/api/v1/production-tasks/{task_id}", json={"priority": "low"}
        ).status_code
        == 409
    )
    assert client.post(f"/api/v1/production-tasks/{task_id}/pause").status_code == 200
    assert (
        client.patch(
            f"/api/v1/production-tasks/{task_id}", json={"planned_quantity": "8"}
        ).status_code
        == 409
    )
    assert (
        client.patch(
            f"/api/v1/production-tasks/{task_id}", json={"priority": "urgent"}
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/v1/production-tasks/{task_id}", json={"machine_id": machine_id}
        ).status_code
        == 200
    )
    assert client.post(f"/api/v1/production-tasks/{task_id}/cancel").status_code == 200
    assert (
        client.patch(
            f"/api/v1/production-tasks/{task_id}", json={"notes": "x"}
        ).status_code
        == 409
    )


def test_actions_and_invalid_transitions(client: TestClient) -> None:
    order_id = create_order(client)
    task = create_task(client, order_id)
    task_id = task["id"]
    assert client.post(f"/api/v1/production-tasks/{task_id}/pause").status_code == 409
    assert client.post(f"/api/v1/production-tasks/{task_id}/finish").status_code == 409
    started = client.post(f"/api/v1/production-tasks/{task_id}/start")
    assert started.status_code == 200
    started_at = started.json()["started_at"]
    paused = client.post(f"/api/v1/production-tasks/{task_id}/pause")
    assert paused.status_code == 200
    assert client.post(f"/api/v1/production-tasks/{task_id}/finish").status_code == 409
    resumed = client.post(f"/api/v1/production-tasks/{task_id}/resume")
    assert resumed.status_code == 200
    assert resumed.json()["started_at"] == started_at
    finished = client.post(f"/api/v1/production-tasks/{task_id}/finish")
    assert finished.status_code == 200
    assert finished.json()["status"] == "physically_completed"
    assert finished.json()["physically_completed_at"] is not None
    assert client.post(f"/api/v1/production-tasks/{task_id}/start").status_code == 409
    assert client.post(f"/api/v1/production-tasks/{task_id}/cancel").status_code == 409
    assert (
        client.patch(
            f"/api/v1/production-tasks/{task_id}", json={"notes": "x"}
        ).status_code
        == 409
    )


def test_machine_busy_pause_resume_parallel_and_manual(client: TestClient) -> None:
    order_id = create_order(client)
    first_machine = create_machine(client)
    second_machine = create_machine(client)
    first = create_task(client, order_id, machine_id=first_machine)
    blocked = create_task(client, order_id, machine_id=first_machine)
    parallel = create_task(client, order_id, machine_id=second_machine)
    manual_one = create_task(client, order_id)
    manual_two = create_task(client, order_id)

    assert (
        client.post(f"/api/v1/production-tasks/{first['id']}/start").status_code == 200
    )
    assert (
        client.post(f"/api/v1/production-tasks/{blocked['id']}/start").status_code
        == 409
    )
    assert (
        client.post(f"/api/v1/production-tasks/{parallel['id']}/start").status_code
        == 200
    )
    assert (
        client.post(f"/api/v1/production-tasks/{manual_one['id']}/start").status_code
        == 200
    )
    assert (
        client.post(f"/api/v1/production-tasks/{manual_two['id']}/start").status_code
        == 200
    )
    assert (
        client.post(f"/api/v1/production-tasks/{first['id']}/pause").status_code == 200
    )
    assert (
        client.post(f"/api/v1/production-tasks/{blocked['id']}/start").status_code
        == 200
    )
    assert (
        client.post(f"/api/v1/production-tasks/{first['id']}/resume").status_code == 409
    )


def test_finish_changes_neither_stock_nor_origin(client: TestClient) -> None:
    supply = client.post(
        "/api/v1/supplies",
        json={
            "name": "PLA producción API",
            "sku": f"PLA-{uuid4()}",
            "category": "material",
            "base_unit": "g",
        },
    )
    assert supply.status_code == 201
    supply_id = str(supply.json()["id"])
    assert (
        client.post(
            f"/api/v1/supplies/{supply_id}/purchases",
            json={
                "quantity": "1000",
                "total_cost": "18000",
                "currency": "ARS",
                "purchased_at": "2026-09-05T10:00:00Z",
            },
        ).status_code
        == 201
    )
    order_id = create_order(client)
    task = create_task(client, order_id)
    stock_before = client.get(f"/api/v1/supplies/{supply_id}/stock").json()["quantity"]
    with SessionFactory() as session:
        movements_before = session.scalar(
            select(func.count()).select_from(SupplyStockMovement)
        )
        order_before = session.get(Order, order_id)
        assert order_before is not None
        status_before = order_before.status

    for action in ("start", "pause", "resume", "finish"):
        assert (
            client.post(f"/api/v1/production-tasks/{task['id']}/{action}").status_code
            == 200
        )

    with SessionFactory() as session:
        assert (
            session.scalar(select(func.count()).select_from(SupplyStockMovement))
            == movements_before
        )
        order_after = session.get(Order, order_id)
        assert order_after is not None
        assert order_after.status == status_before
        assert session.scalar(select(func.count()).select_from(Project)) == 0
    stock_after = client.get(f"/api/v1/supplies/{supply_id}/stock").json()["quantity"]
    assert Decimal(stock_before) == Decimal("1000")
    assert Decimal(stock_after) == Decimal("1000")
    assert client.delete(f"/api/v1/production-tasks/{task['id']}").status_code == 405


def test_finish_does_not_change_project(client: TestClient) -> None:
    project_id, component_id = create_project(client)
    task = client.post(
        f"/api/v1/project-components/{component_id}/production-tasks",
        json=task_payload(),
    ).json()
    before = client.get(f"/api/v1/projects/{project_id}").json()["status"]

    mark_legacy(str(task["id"]))
    assert (
        client.post(f"/api/v1/production-tasks/{task['id']}/start").status_code == 200
    )
    assert (
        client.post(f"/api/v1/production-tasks/{task['id']}/finish").status_code == 200
    )
    assert client.get(f"/api/v1/projects/{project_id}").json()["status"] == before
