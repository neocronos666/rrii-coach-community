from collections.abc import Iterator
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.integration.conftest import clear_test_database
from tests.integration.test_hito9_runs import new_task, start
from tests.integration.test_production_api import create_project

pytestmark = pytest.mark.integration


@pytest.fixture
def client() -> Iterator[TestClient]:
    clear_test_database()
    with TestClient(app) as client:
        yield client
    clear_test_database()


def supply(client: TestClient) -> str:
    response = client.post(
        "/api/v1/supplies",
        json={
            "name": "PLA",
            "category": "material",
            "base_unit": "g",
        },
    )
    assert response.status_code == 201
    return str(response.json()["id"])


def reserve(
    client: TestClient, task: str, supply_id: str, quantity: str
) -> dict[str, object]:
    response = client.put(
        f"/api/v1/production-tasks/{task}/supply-reservations/{supply_id}",
        json={"quantity": quantity},
    )
    assert response.status_code == 200, response.text
    return dict(response.json())


def test_overbooking_warns_without_stock_mutation(client: TestClient) -> None:
    material = supply(client)
    a, b = new_task(client), new_task(client)
    assert (
        client.post(
            f"/api/v1/supplies/{material}/adjustments",
            json={
                "direction": "in",
                "quantity": "1000",
                "reason": "Existencia inicial",
                "occurred_at": "2026-09-01T00:00:00Z",
            },
        ).status_code
        == 201
    )
    reserve(client, a, material, "600")
    reserve(client, b, material, "500")
    result = client.get(f"/api/v1/supplies/{material}/availability").json()
    assert Decimal(result["physical_quantity"]) == 1000
    assert Decimal(result["reserved_quantity"]) == 1100
    assert Decimal(result["available_quantity"]) == -100
    assert result["shortage_warning"] is True
    assert len(client.get(f"/api/v1/supplies/{material}/movements").json()) == 1
    reserve(client, a, material, "600")
    assert (
        len(client.get(f"/api/v1/production-tasks/{a}/supply-reservations").json()) == 1
    )
    reserve(client, b, material, "0")
    assert (
        client.get(f"/api/v1/supplies/{material}/availability").json()[
            "shortage_warning"
        ]
        is False
    )


def test_task_completion_and_cancellation_release_reservations(
    client: TestClient,
) -> None:
    material = supply(client)
    task = new_task(client)
    reserve(client, task, material, "500")
    run = start(client, task)
    assert (
        client.post(
            f"/api/v1/production-runs/{run}/close", json={"good_quantity": "10"}
        ).status_code
        == 200
    )
    assert (
        Decimal(
            client.get(f"/api/v1/supplies/{material}/availability").json()[
                "reserved_quantity"
            ]
        )
        == 0
    )
    assert (
        client.put(
            f"/api/v1/production-tasks/{task}/supply-reservations/{material}",
            json={"quantity": "1"},
        ).status_code
        == 409
    )
    another = new_task(client)
    reserve(client, another, material, "200")
    assert client.post(f"/api/v1/production-tasks/{another}/cancel").status_code == 200
    assert (
        Decimal(
            client.get(f"/api/v1/supplies/{material}/availability").json()[
                "reserved_quantity"
            ]
        )
        == 0
    )


def test_parent_cancellation_releases_and_prevents_new_reservations(
    client: TestClient,
) -> None:
    material = supply(client)
    task = new_task(client)
    reserve(client, task, material, "100")
    order = client.get(f"/api/v1/production-tasks/{task}").json()["order_id"]
    assert client.post(f"/api/v1/orders/{order}/cancel").status_code == 200
    assert (
        Decimal(
            client.get(f"/api/v1/supplies/{material}/availability").json()[
                "reserved_quantity"
            ]
        )
        == 0
    )
    assert (
        client.put(
            f"/api/v1/production-tasks/{task}/supply-reservations/{material}",
            json={"quantity": "1"},
        ).status_code
        == 409
    )
    project, component = create_project(client)
    created = client.post(
        f"/api/v1/project-components/{component}/production-tasks",
        json={
            "title": "Componente",
            "task_type": "manual",
            "planned_quantity": "1",
        },
    )
    assert created.status_code == 201
    reserve(client, str(created.json()["id"]), material, "30")
    assert client.post(f"/api/v1/projects/{project}/cancel").status_code == 200
    assert (
        Decimal(
            client.get(f"/api/v1/supplies/{material}/availability").json()[
                "reserved_quantity"
            ]
        )
        == 0
    )


def test_units_and_invalid_reservations(client: TestClient) -> None:
    material = supply(client)
    task = new_task(client)
    reserve(client, task, material, "10")
    assert (
        client.patch(
            f"/api/v1/supplies/{material}", json={"base_unit": "kg"}
        ).status_code
        == 409
    )
    reserve(client, task, material, "0")
    assert (
        client.patch(
            f"/api/v1/supplies/{material}", json={"base_unit": "kg"}
        ).status_code
        == 409
    )
    path = f"/api/v1/production-tasks/{task}/supply-reservations/{material}"
    assert client.put(path, json={"quantity": "-1"}).status_code == 422
    assert client.put(path, json={"quantity": "1", "unit": "kg"}).status_code == 422
    assert client.get(f"/api/v1/supplies/{uuid4()}/availability").status_code == 404
    assert (
        client.patch(f"/api/v1/supplies/{material}", json={"active": False}).status_code
        == 200
    )
    assert client.put(path, json={"quantity": "1"}).status_code == 409
