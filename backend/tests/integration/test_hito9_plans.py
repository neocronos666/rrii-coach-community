from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.integration.conftest import clear_test_database
from tests.integration.test_hito9_recipes import setup_recipe, step
from tests.integration.test_hito9_runs import start
from tests.integration.test_production_api import (
    create_machine,
    create_order,
    create_project,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def client() -> Iterator[TestClient]:
    clear_test_database()
    with TestClient(app) as client:
        yield client
    clear_test_database()


def recipe_with_components(client: TestClient) -> tuple[str, str, str, str]:
    recipe, final = setup_recipe(client)
    _, component = setup_recipe(client)
    supply = client.post(
        "/api/v1/supplies",
        json={"name": "Pegamento", "category": "consumable", "base_unit": "ml"},
    ).json()["id"]
    body = {
        "steps": [
            {
                **step("print"),
                "output_variant_id": component,
                "quantity_per_output": "4",
            },
            {
                **step("assemble", ["print"]),
                "output_variant_id": final,
                "product_inputs": [
                    {
                        "product_variant_id": component,
                        "quantity_per_batch": "48",
                        "source_step_key": "print",
                    }
                ],
                "supply_inputs": [{"supply_id": supply, "quantity_per_batch": "3"}],
            },
            {**step("pack", ["assemble"]), "batch_yield": "1"},
        ]
    }
    response = client.put(f"/api/v1/recipes/{recipe}/plan", json=body)
    assert response.status_code == 200, response.text
    return recipe, final, component, str(supply)


def test_plan_rounding_snapshot_and_complete_physical_flow(client: TestClient) -> None:
    recipe, final, component, supply = recipe_with_components(client)
    preview = client.post(
        f"/api/v1/recipes/{recipe}/production-preview", json={"target_quantity": "10"}
    )
    assert preview.status_code == 200, preview.text
    calculated = {s["key"]: s for s in preview.json()["steps"]}
    assert Decimal(calculated["print"]["required_quantity"]) == 48
    assert Decimal(calculated["print"]["batches"]) == 4
    order = create_order(client)
    body = {"request_id": str(uuid4()), "recipe_id": recipe, "target_quantity": "10"}
    response = client.post(f"/api/v1/orders/{order}/production-plans", json=body)
    assert response.status_code == 201, response.text
    plan = response.json()
    tasks = {task["recipe_step_key"]: task for task in plan["tasks"]}
    assert all(task["origin"] == "recipe" for task in plan["tasks"])
    assert (
        Decimal(
            client.get(
                f"/api/v1/production-tasks/{tasks['assemble']['id']}/supply-reservations"
            ).json()[0]["quantity"]
        )
        == 3
    )
    assert (
        client.post(
            f"/api/v1/production-tasks/{tasks['assemble']['id']}/runs",
            json={"request_id": str(uuid4())},
        ).status_code
        == 409
    )
    assert (
        client.patch(
            f"/api/v1/production-tasks/{tasks['print']['id']}",
            json={"planned_quantity": "1"},
        ).status_code
        == 409
    )
    saved_snapshot = plan["snapshot"]
    assert (
        client.put(
            f"/api/v1/recipes/{recipe}/plan",
            json={"steps": [{**step("replacement"), "output_variant_id": final}]},
        ).status_code
        == 200
    )
    assert (
        client.get(f"/api/v1/production-plans/{plan['id']}").json()["snapshot"]
        == saved_snapshot
    )
    assert (
        client.post(f"/api/v1/orders/{order}/production-plans", json=body).json()["id"]
        == plan["id"]
    )
    run = start(client, tasks["print"]["id"])
    assert (
        client.post(
            f"/api/v1/production-runs/{run}/close", json={"good_quantity": "48"}
        ).status_code
        == 200
    )
    run = start(client, tasks["assemble"]["id"])
    missing = client.post(
        f"/api/v1/production-runs/{run}/close", json={"good_quantity": "12"}
    )
    assert missing.status_code == 409
    assert client.get(f"/api/v1/production-runs/{run}").json()["status"] == "running"
    closed = client.post(
        f"/api/v1/production-runs/{run}/close",
        json={
            "good_quantity": "12",
            "product_consumptions": [{"variant_id": component, "consumed": "48"}],
            "supply_consumptions": [{"supply_id": supply, "consumed": "3"}],
        },
    )
    assert closed.status_code == 200, closed.text
    stock = client.get(f"/api/v1/product-variants/{final}/stock").json()
    assert Decimal(stock["physical_quantity"]) == 12
    assert Decimal(stock["allocated_quantity"]) == 10
    assert Decimal(stock["available_quantity"]) == 2
    run = start(client, tasks["pack"]["id"])
    assert (
        client.post(
            f"/api/v1/production-runs/{run}/close", json={"good_quantity": "10"}
        ).status_code
        == 200
    )
    assert (
        len(client.get(f"/api/v1/product-variants/{final}/stock-movements").json()) == 1
    )
    assert client.get(f"/api/v1/orders/{order}").json()["status"] == "pending"
    assert (
        client.post(
            f"/api/v1/product-allocations/{plan['allocation_id']}/deliver",
            json={"request_id": str(uuid4()), "quantity": "10"},
        ).status_code
        == 201
    )
    assert (
        Decimal(
            client.get(f"/api/v1/product-variants/{final}/stock").json()[
                "physical_quantity"
            ]
        )
        == 2
    )


def test_concurrent_generation_is_atomic_and_idempotent(client: TestClient) -> None:
    recipe, _, _, _ = recipe_with_components(client)
    project, component = create_project(client)
    body = {
        "request_id": str(uuid4()),
        "recipe_id": recipe,
        "target_quantity": "2",
        "allocate_output": False,
        "reserve_supplies": False,
    }
    path = f"/api/v1/project-components/{component}/production-plans"

    def create(_: int) -> dict[str, object]:
        with TestClient(app) as parallel:
            response = parallel.post(path, json=body)
            assert response.status_code == 201, response.text
            return dict(response.json())

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(create, [1, 2]))
    assert first["id"] == second["id"]
    assert first["allocation_id"] is None
    assert client.get("/api/v1/product-allocations").json() == []
    tasks = client.get(
        "/api/v1/production-tasks", params={"project_id": project}
    ).json()
    assert len(tasks) == 3
    for task in tasks:
        assert (
            client.get(
                f"/api/v1/production-tasks/{task['id']}/supply-reservations"
            ).json()
            == []
        )
    assert client.post(path, json={**body, "target_quantity": "3"}).status_code == 409
    assert client.post(f"/api/v1/projects/{project}/cancel").status_code == 200
    assert client.post(path, json=body).status_code == 201
    assert (
        client.post(path, json={**body, "request_id": str(uuid4())}).status_code == 409
    )


def test_required_machine_snapshot_survives_recipe_change(client: TestClient) -> None:
    recipe, final = setup_recipe(client)
    incompatible = create_machine(client)
    machine = client.post(
        "/api/v1/machines", json={"name": "FDM real", "machine_type": "fdm_printer"}
    )
    assert machine.status_code == 201, machine.text
    fdm = machine.json()["id"]
    assert (
        client.put(
            f"/api/v1/recipes/{recipe}/plan",
            json={
                "steps": [
                    {
                        **step("print"),
                        "output_variant_id": final,
                        "required_machine_type": "fdm_printer",
                    }
                ]
            },
        ).status_code
        == 200
    )
    order = create_order(client)
    response = client.post(
        f"/api/v1/orders/{order}/production-plans",
        json={"request_id": str(uuid4()), "recipe_id": recipe, "target_quantity": "1"},
    )
    assert response.status_code == 201, response.text
    task = response.json()["tasks"][0]["id"]
    path = f"/api/v1/production-tasks/{task}/runs"
    assert (
        client.post(
            path, json={"request_id": str(uuid4()), "machine_id": None}
        ).status_code
        == 409
    )
    assert (
        client.post(
            path, json={"request_id": str(uuid4()), "machine_id": incompatible}
        ).status_code
        == 409
    )
    assert (
        client.put(
            f"/api/v1/recipes/{recipe}/plan",
            json={"steps": [{**step("manual"), "output_variant_id": final}]},
        ).status_code
        == 200
    )
    assert (
        client.post(
            path, json={"request_id": str(uuid4()), "machine_id": fdm}
        ).status_code
        == 201
    )


def test_generation_rejects_incomplete_recipe_without_partial_writes(
    client: TestClient,
) -> None:
    recipe, _ = setup_recipe(client)
    order = create_order(client)
    response = client.post(
        f"/api/v1/orders/{order}/production-plans",
        json={"request_id": str(uuid4()), "recipe_id": recipe, "target_quantity": "10"},
    )
    assert response.status_code == 409, response.text
    assert (
        client.get("/api/v1/production-tasks", params={"order_id": order}).json() == []
    )
    assert client.get("/api/v1/product-allocations").json() == []
