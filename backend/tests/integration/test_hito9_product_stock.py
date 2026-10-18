from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.integration.conftest import clear_test_database
from tests.integration.test_hito9_runs import start
from tests.integration.test_production_api import create_order

pytestmark = pytest.mark.integration


@pytest.fixture
def client() -> Iterator[TestClient]:
    clear_test_database()
    with TestClient(app) as client:
        yield client
    clear_test_database()


def variant(client: TestClient) -> str:
    response = client.post(
        "/api/v1/products",
        json={
            "name": "Pieza",
            "initial_variant": {"name": "Roja", "base_unit": "unit"},
        },
    )
    assert response.status_code == 201, response.text
    return str(response.json()["initial_variant"]["id"])


def test_manual_ledger_retry_and_negative_stock(client: TestClient) -> None:
    item = variant(client)
    path = f"/api/v1/product-variants/{item}"
    body = {
        "request_id": str(uuid4()),
        "movement_type": "purchase",
        "quantity": "12",
        "reason": "Compra inicial",
    }
    first = client.post(path + "/stock-movements", json=body)
    assert first.status_code == 201, first.text
    assert (
        client.post(path + "/stock-movements", json=body).json()["id"]
        == first.json()["id"]
    )
    assert (
        client.post(
            path + "/stock-movements", json={**body, "quantity": "13"}
        ).status_code
        == 409
    )
    assert (
        client.post(
            path + "/stock-movements",
            json={
                **body,
                "request_id": str(uuid4()),
                "movement_type": "adjustment_out",
                "quantity": "15",
            },
        ).status_code
        == 201
    )
    stock = client.get(path + "/stock").json()
    assert Decimal(stock["physical_quantity"]) == -3
    assert stock["shortage_warning"] is True
    assert len(client.get(path + "/stock-movements").json()) == 2
    assert (
        client.post(
            path + "/stock-movements", json={**body, "movement_type": "production"}
        ).status_code
        == 422
    )


def test_production_excess_is_physical_and_retry_does_not_duplicate(
    client: TestClient,
) -> None:
    item = variant(client)
    order = create_order(client)
    response = client.post(
        f"/api/v1/orders/{order}/production-tasks",
        json={
            "title": "Fabricar",
            "task_type": "manual",
            "planned_quantity": "10",
            "planned_unit": "unit",
            "output_variant_id": item,
        },
    )
    assert response.status_code == 201, response.text
    task = response.json()["id"]
    run = start(client, task)
    payload = {
        "good_quantity": "12",
        "failed_quantity": "1",
        "failure_reason": "quality_failure",
    }

    def close(_: int) -> int:
        with TestClient(app) as parallel:
            return parallel.post(
                f"/api/v1/production-runs/{run}/close", json=payload
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(close, [1, 2])) == [200, 200]
    path = f"/api/v1/product-variants/{item}"
    assert Decimal(client.get(path + "/stock").json()["physical_quantity"]) == 12
    movements = client.get(path + "/stock-movements").json()
    assert len(movements) == 1
    assert movements[0]["run_id"] == run
    assert (
        client.get(f"/api/v1/production-tasks/{task}").json()["status"]
        == "physically_completed"
    )
