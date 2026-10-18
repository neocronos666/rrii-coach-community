from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.integration.conftest import clear_test_database
from tests.integration.test_hito9_product_stock import variant
from tests.integration.test_hito9_runs import start
from tests.integration.test_production_api import create_order

pytestmark = pytest.mark.integration


@pytest.fixture
def client() -> Iterator[TestClient]:
    clear_test_database()
    with TestClient(app) as client:
        yield client
    clear_test_database()


def output_run(client: TestClient, item: str) -> str:
    order = create_order(client)
    task = client.post(
        f"/api/v1/orders/{order}/production-tasks",
        json={
            "title": "Ensamblar",
            "task_type": "manual",
            "planned_quantity": "2",
            "planned_unit": "unit",
            "output_variant_id": item,
        },
    )
    assert task.status_code == 201, task.text
    return start(client, task.json()["id"])


def test_composition_atomic_idempotent_and_waste_subset(client: TestClient) -> None:
    component, output = variant(client), variant(client)
    path = f"/api/v1/product-variants/{component}"
    assert (
        client.post(
            path + "/stock-movements",
            json={
                "request_id": str(uuid4()),
                "movement_type": "purchase",
                "quantity": "10",
                "reason": "Componentes",
            },
        ).status_code
        == 201
    )
    run = output_run(client, output)
    payload = {
        "good_quantity": "2",
        "product_consumptions": [
            {"variant_id": component, "consumed": "9", "wasted": "1"}
        ],
    }

    def close(_: int) -> int:
        with TestClient(app) as parallel:
            return parallel.post(
                f"/api/v1/production-runs/{run}/close", json=payload
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(close, [1, 2])) == [200, 200]
    assert Decimal(client.get(path + "/stock").json()["physical_quantity"]) == 1
    assert (
        Decimal(
            client.get(f"/api/v1/product-variants/{output}/stock").json()[
                "physical_quantity"
            ]
        )
        == 2
    )
    consumptions = client.get(
        f"/api/v1/production-runs/{run}/product-consumptions"
    ).json()
    assert len(consumptions) == 1
    movements = client.get(path + "/stock-movements").json()
    assert movements[-1]["run_consumption_id"] == consumptions[0]["id"]
    assert Decimal(movements[-1]["quantity"]) == -9


def test_missing_component_rolls_back_output_and_result(client: TestClient) -> None:
    output = variant(client)
    run = output_run(client, output)
    path = f"/api/v1/production-runs/{run}"
    payload = {
        "good_quantity": "2",
        "product_consumptions": [{"variant_id": str(uuid4()), "consumed": "1"}],
    }
    assert client.post(path + "/close", json=payload).status_code == 404
    assert client.get(path).json()["status"] == "running"
    assert (
        Decimal(
            client.get(f"/api/v1/product-variants/{output}/stock").json()[
                "physical_quantity"
            ]
        )
        == 0
    )
    payload["product_consumptions"] = [{"variant_id": output, "consumed": "1"}]
    assert client.post(path + "/close", json=payload).status_code == 409
    payload["product_consumptions"] = [
        {"variant_id": output, "consumed": "1", "wasted": "2"}
    ]
    assert client.post(path + "/close", json=payload).status_code == 422


def test_unregistered_component_stock_warns_but_records_reality(
    client: TestClient,
) -> None:
    component, output = variant(client), variant(client)
    run = output_run(client, output)
    payload = {
        "good_quantity": "0",
        "failed_quantity": "1",
        "failure_reason": "operator_error",
        "product_consumptions": [
            {"variant_id": component, "consumed": "4", "wasted": "4"}
        ],
    }
    response = client.post(f"/api/v1/production-runs/{run}/close", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["warnings"] == ["insufficient_product_stock:" + component]
    assert (
        Decimal(
            client.get(f"/api/v1/product-variants/{component}/stock").json()[
                "physical_quantity"
            ]
        )
        == -4
    )
    assert client.get(f"/api/v1/product-variants/{output}/stock-movements").json() == []
