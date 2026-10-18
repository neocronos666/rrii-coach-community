from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.integration.conftest import clear_test_database
from tests.integration.test_hito9_product_stock import variant
from tests.integration.test_production_api import create_order, create_project

pytestmark = pytest.mark.integration


@pytest.fixture
def client() -> Iterator[TestClient]:
    clear_test_database()
    with TestClient(app) as client:
        yield client
    clear_test_database()


def test_allocation_preserves_physical_stock_and_delivery_subtracts_once(
    client: TestClient,
) -> None:
    item, order = variant(client), create_order(client)
    path = f"/api/v1/product-variants/{item}"
    assert (
        client.post(
            path + "/stock-movements",
            json={
                "request_id": str(uuid4()),
                "movement_type": "purchase",
                "quantity": "12",
                "reason": "Ingreso",
            },
        ).status_code
        == 201
    )
    payload = {
        "request_id": str(uuid4()),
        "variant_id": item,
        "order_id": order,
        "quantity": "10",
    }
    response = client.post("/api/v1/product-allocations", json=payload)
    assert response.status_code == 201, response.text
    result = response.json()
    assert Decimal(result["stock"]["physical_quantity"]) == 12
    assert Decimal(result["stock"]["allocated_quantity"]) == 10
    assert Decimal(result["stock"]["available_quantity"]) == 2
    allocation = result["allocation"]["id"]
    assert (
        client.post("/api/v1/product-allocations", json=payload).json()["allocation"][
            "id"
        ]
        == allocation
    )
    assert (
        client.post(
            "/api/v1/product-allocations", json={**payload, "quantity": "11"}
        ).status_code
        == 409
    )
    delivery = {"request_id": str(uuid4()), "quantity": "4"}

    def deliver(_: int) -> int:
        with TestClient(app) as parallel:
            return parallel.post(
                f"/api/v1/product-allocations/{allocation}/deliver", json=delivery
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(deliver, [1, 2])) == [201, 201]
    stock = client.get(path + "/stock").json()
    assert Decimal(stock["physical_quantity"]) == 8
    assert Decimal(stock["allocated_quantity"]) == 6
    assert Decimal(stock["available_quantity"]) == 2
    assert len(client.get(path + "/stock-movements").json()) == 2
    assert (
        client.post(
            f"/api/v1/product-allocations/{allocation}/deliver",
            json={"request_id": str(uuid4()), "quantity": "7"},
        ).status_code
        == 409
    )
    assert (
        client.post(f"/api/v1/product-allocations/{allocation}/release").status_code
        == 200
    )
    assert Decimal(client.get(path + "/stock").json()["available_quantity"]) == 8
    assert (
        Decimal(
            client.post("/api/v1/product-allocations", json=payload).json()[
                "allocation"
            ]["quantity"]
        )
        == 0
    )


def test_cancellation_releases_allocations_but_preserves_delivery(
    client: TestClient,
) -> None:
    item, order = variant(client), create_order(client)
    payload = {
        "request_id": str(uuid4()),
        "variant_id": item,
        "order_id": order,
        "quantity": "10",
    }
    response = client.post("/api/v1/product-allocations", json=payload)
    assert response.status_code == 201, response.text
    assert response.json()["stock"]["shortage_warning"] is True
    allocation = response.json()["allocation"]["id"]
    delivery = {"request_id": str(uuid4()), "quantity": "2"}
    path = f"/api/v1/product-allocations/{allocation}"
    assert client.post(path + "/deliver", json=delivery).status_code == 201
    assert client.post(f"/api/v1/orders/{order}/cancel").status_code == 200
    assert Decimal(client.get(path).json()["quantity"]) == 0
    assert client.post(path + "/deliver", json=delivery).status_code == 201
    assert (
        client.post(
            path + "/deliver", json={**delivery, "request_id": str(uuid4())}
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/v1/product-allocations", json={**payload, "request_id": str(uuid4())}
        ).status_code
        == 409
    )
    stock = client.get(f"/api/v1/product-variants/{item}/stock").json()
    assert Decimal(stock["physical_quantity"]) == -2
    assert Decimal(stock["allocated_quantity"]) == 0


def test_project_destination_and_validation(client: TestClient) -> None:
    item = variant(client)
    project, component = create_project(client)
    payload = {
        "request_id": str(uuid4()),
        "variant_id": item,
        "project_component_id": component,
        "quantity": "3",
    }
    response = client.post("/api/v1/product-allocations", json=payload)
    assert response.status_code == 201, response.text
    allocation = response.json()["allocation"]["id"]
    assert (
        client.post(
            "/api/v1/product-allocations", json={**payload, "order_id": str(uuid4())}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/product-allocations",
            json={
                **payload,
                "project_component_id": str(uuid4()),
                "request_id": str(uuid4()),
            },
        ).status_code
        == 404
    )
    assert client.post(f"/api/v1/projects/{project}/cancel").status_code == 200
    assert (
        Decimal(
            client.get(f"/api/v1/product-allocations/{allocation}").json()["quantity"]
        )
        == 0
    )
    assert (
        len(
            client.get(
                "/api/v1/product-allocations",
                params={"project_component_id": component},
            ).json()
        )
        == 1
    )
