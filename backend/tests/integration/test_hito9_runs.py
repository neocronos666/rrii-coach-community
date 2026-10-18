from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.integration.conftest import clear_test_database
from tests.integration.test_production_api import (
    create_machine,
    create_order,
    mark_legacy,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def client() -> Iterator[TestClient]:
    clear_test_database()
    with TestClient(app) as client:
        yield client
    clear_test_database()


def new_task(
    client: TestClient, machine: str | None = None, quantity: str = "10"
) -> str:
    order = create_order(client)
    response = client.post(
        f"/api/v1/orders/{order}/production-tasks",
        json={
            "title": "Objetivo",
            "task_type": "manual",
            "planned_quantity": quantity,
            "planned_unit": "unit",
            "machine_id": machine,
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["execution_mode"] == "runs"
    return str(response.json()["id"])


def start(client: TestClient, task: str) -> str:
    response = client.post(
        f"/api/v1/production-tasks/{task}/runs", json={"request_id": str(uuid4())}
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def test_partial_failures_and_completion(client: TestClient) -> None:
    task = new_task(client)
    first = start(client, task)
    path = f"/api/v1/production-tasks/{task}"
    assert client.post(path + "/pause").status_code == 409
    assert client.post(path + "/cancel").status_code == 409
    assert client.post(path + "/finish").status_code == 409
    result = {
        "good_quantity": "4",
        "failed_quantity": "6",
        "failure_reason": "power_failure",
    }
    closed = client.post(f"/api/v1/production-runs/{first}/close", json=result)
    assert closed.status_code == 200, closed.text
    assert client.get(path).json()["status"] == "in_progress"
    assert (
        client.post(f"/api/v1/production-runs/{first}/close", json=result).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/production-runs/{first}/close", json={"good_quantity": "5"}
        ).status_code
        == 409
    )
    assert client.post(path + "/pause").status_code == 200
    assert (
        client.post(path + "/runs", json={"request_id": str(uuid4())}).status_code
        == 409
    )
    assert client.post(path + "/resume").status_code == 200
    second = start(client, task)
    assert (
        client.post(
            f"/api/v1/production-runs/{second}/close", json={"good_quantity": "8"}
        ).status_code
        == 200
    )
    assert client.get(path).json()["status"] == "physically_completed"
    progress = client.get(path + "/progress").json()
    assert Decimal(progress["good_quantity"]) == 12
    assert Decimal(progress["failed_quantity"]) == 6
    assert Decimal(progress["excess_quantity"]) == 2
    assert progress["closed_runs"] == 2
    assert (
        client.post(path + "/runs", json={"request_id": str(uuid4())}).status_code
        == 409
    )


def test_machine_released_between_runs_and_legacy_exclusivity(
    client: TestClient,
) -> None:
    machine = create_machine(client)
    a, b = new_task(client, machine), new_task(client, machine)
    run = start(client, a)
    assert (
        client.post(
            f"/api/v1/production-tasks/{b}/runs", json={"request_id": str(uuid4())}
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/v1/production-runs/{run}/close", json={"good_quantity": "1"}
        ).status_code
        == 200
    )
    second = start(client, b)
    assert client.get(f"/api/v1/production-tasks/{a}").json()["status"] == "in_progress"
    legacy = new_task(client, machine)
    mark_legacy(legacy)
    assert client.post(f"/api/v1/production-tasks/{legacy}/start").status_code == 409
    assert (
        client.post(
            f"/api/v1/production-runs/{second}/close", json={"good_quantity": "1"}
        ).status_code
        == 200
    )
    assert client.post(f"/api/v1/production-tasks/{legacy}/start").status_code == 200
    assert (
        client.post(
            f"/api/v1/production-tasks/{a}/runs", json={"request_id": str(uuid4())}
        ).status_code
        == 409
    )


def test_start_retry_and_concurrent_machine_claim(client: TestClient) -> None:
    machine = create_machine(client)
    a, b = new_task(client, machine), new_task(client, machine)
    body = {"request_id": str(uuid4())}
    first = client.post(f"/api/v1/production-tasks/{a}/runs", json=body)
    assert first.status_code == 201
    retry = client.post(f"/api/v1/production-tasks/{a}/runs", json=body)
    assert retry.json()["id"] == first.json()["id"]
    assert (
        client.post(f"/api/v1/production-tasks/{b}/runs", json=body).status_code == 409
    )
    client.post(
        f"/api/v1/production-runs/{first.json()['id']}/close",
        json={"good_quantity": "0"},
    )

    def claim(task_id: str) -> int:
        with TestClient(app) as parallel:
            return parallel.post(
                f"/api/v1/production-tasks/{task_id}/runs",
                json={"request_id": str(uuid4())},
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(claim, [a, b])) == [201, 409]


def test_validation_and_cancelled_origin(client: TestClient) -> None:
    task = new_task(client)
    path = f"/api/v1/production-tasks/{task}"
    assert client.patch(path, json={"execution_mode": "legacy"}).status_code == 422
    assert (
        client.post(
            path + "/runs",
            json={"request_id": str(uuid4()), "started_at": "2026-01-01T10:00:00"},
        ).status_code
        == 422
    )
    run = start(client, task)
    assert (
        client.post(
            f"/api/v1/production-runs/{run}/close", json={"good_quantity": "-1"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/v1/production-runs/{run}/close",
            json={"good_quantity": "0", "ended_at": "2000-01-01T00:00:00Z"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/v1/production-runs/{run}/close",
            json={"good_quantity": "0", "failure_reason": "machine_failure"},
        ).status_code
        == 200
    )
    order = client.get(path).json()["order_id"]
    assert client.post(f"/api/v1/orders/{order}/cancel").status_code == 200
    assert (
        client.post(path + "/runs", json={"request_id": str(uuid4())}).status_code
        == 409
    )
