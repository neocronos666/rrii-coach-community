from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionFactory
from app.modules.production.plan_models import ProductionPlan
from app.modules.production.run_models import ProductionRun
from tests.integration import test_hito10b_options as catalog_tests
from tests.integration.test_hito9_recipes import setup_recipe
from tests.integration.test_production_api import create_order

pytestmark = pytest.mark.integration
client = catalog_tests.client


def machine(
    client: TestClient, name: str, *, active: bool = True, kind: str = "fdm_printer"
) -> str:
    response = client.post(
        "/api/v1/machines", json={"name": name, "machine_type": kind, "active": active}
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def recipe_plan(client: TestClient) -> tuple[str, dict[str, Any]]:
    recipe, variant = setup_recipe(client)
    body = {
        "steps": [
            {
                "key": "print",
                "title": "Imprimir",
                "task_type": "fdm_print",
                "required_machine_type": "fdm_printer",
                "output_variant_id": variant,
            },
            {
                "key": "dry",
                "title": "Dejar secar",
                "kind": "wait",
                "depends_on": ["print"],
            },
        ]
    }
    response = client.put(f"/api/v1/recipes/{recipe}/plan", json=body)
    assert response.status_code == 200, response.text
    return recipe, response.json()


def test_same_recipe_different_machines_and_unassigned_plan(client: TestClient) -> None:
    recipe, saved = recipe_plan(client)
    first = machine(client, "Primera")
    second = machine(client, "Segunda")
    order = create_order(client)
    path = f"/api/v1/orders/{order}/production-plans"
    for selected in (first, second, None):
        assignments = {"print": selected} if selected else {}
        payload = {
            "request_id": str(uuid4()),
            "recipe_id": recipe,
            "target_quantity": "2",
            "machine_assignments": assignments,
        }
        response = client.post(path, json=payload)
        assert response.status_code == 201, response.text
        plan = response.json()
        tasks = {task["recipe_step_key"]: task for task in plan["tasks"]}
        assert tasks["print"]["machine_id"] == selected
        assert tasks["dry"]["machine_id"] is None
        assert plan["snapshot"]["machine_assignments"] == assignments
        assert "suggested_machine_id" not in tasks["print"]["recipe_snapshot"]["step"]
        assert (
            tasks["print"]["recipe_snapshot"]["step"]["required_machine_type"]
            == "fdm_printer"
        )
        assert client.post(path, json=payload).json()["id"] == plan["id"]
        assert client.get(f"/api/v1/recipes/{recipe}/plan").json() == saved
    assert len(client.get("/api/v1/machines").json()) == 2
    # La receta tampoco acepta una máquina válida: debe asignarse en producción.
    bad_step = {"key": "print", "title": "Imprimir", "suggested_machine_id": first}
    assert (
        client.put(
            f"/api/v1/recipes/{recipe}/plan", json={"steps": [bad_step]}
        ).status_code
        == 422
    )
    assert client.get(f"/api/v1/recipes/{recipe}/plan").json() == saved


@pytest.mark.parametrize(
    "case", ["unknown_step", "missing", "inactive", "wrong_type", "wait", "service"]
)
def test_invalid_assignment_has_no_partial_writes(
    client: TestClient, case: str
) -> None:
    recipe, saved = recipe_plan(client)
    selected = machine(
        client,
        "Asignada",
        active=case != "inactive",
        kind="sla_printer" if case == "wrong_type" else "fdm_printer",
    )
    key = "print"
    if case == "unknown_step":
        key = "missing"
    elif case == "missing":
        selected = str(uuid4())
    elif case == "wait":
        key = "dry"
    elif case == "service":
        service = client.post(
            "/api/v1/service-definitions", json={"name": "Lijar"}
        ).json()["id"]
        variant = saved["steps"][0]["output_variant_id"]
        assert (
            client.put(
                f"/api/v1/recipes/{recipe}/plan",
                json={
                    "steps": [
                        {
                            "key": "print",
                            "title": "Lijar",
                            "kind": "service",
                            "service_definition_id": service,
                            "output_variant_id": variant,
                        },
                    ]
                },
            ).status_code
            == 200
        )
    order = create_order(client)
    response = client.post(
        f"/api/v1/orders/{order}/production-plans",
        json={
            "request_id": str(uuid4()),
            "recipe_id": recipe,
            "target_quantity": "1",
            "machine_assignments": {key: selected},
        },
    )
    assert response.status_code == 409, response.text
    assert (
        client.get("/api/v1/production-tasks", params={"order_id": order}).json() == []
    )
    assert client.get("/api/v1/product-allocations").json() == []
    with SessionFactory() as session:
        assert session.scalar(select(ProductionPlan)) is None


def test_assignment_is_historical_and_part_of_idempotency(client: TestClient) -> None:
    recipe, saved = recipe_plan(client)
    first = machine(client, "Primera")
    second = machine(client, "Segunda")
    order = create_order(client)
    path = f"/api/v1/orders/{order}/production-plans"
    payload = {
        "request_id": str(uuid4()),
        "recipe_id": recipe,
        "target_quantity": "1",
        "machine_assignments": {"print": first},
    }
    response = client.post(path, json=payload)
    assert response.status_code == 201
    plan = response.json()
    assert (
        client.post(
            path, json={**payload, "machine_assignments": {"print": second}}
        ).status_code
        == 409
    )
    assert (
        client.post(path, json={**payload, "machine_assignments": {}}).status_code
        == 409
    )
    assert (
        client.patch(f"/api/v1/machines/{first}", json={"active": False}).status_code
        == 200
    )
    assert (
        client.put(
            f"/api/v1/recipes/{recipe}/plan",
            json={
                "steps": [
                    {
                        "key": "new",
                        "title": "Otra receta",
                        "output_variant_id": saved["steps"][0]["output_variant_id"],
                    }
                ]
            },
        ).status_code
        == 200
    )
    historical = client.get(f"/api/v1/production-plans/{plan['id']}").json()
    assert historical["snapshot"] == plan["snapshot"]
    assert historical["tasks"] == plan["tasks"]
    assert client.post(path, json=payload).json()["id"] == plan["id"]


def test_legacy_request_without_assignment_field_stays_idempotent(
    client: TestClient,
) -> None:
    recipe, _ = recipe_plan(client)
    order = create_order(client)
    path = f"/api/v1/orders/{order}/production-plans"
    payload = {"request_id": str(uuid4()), "recipe_id": recipe, "target_quantity": "1"}
    response = client.post(path, json=payload)
    assert response.status_code == 201
    plan_id = response.json()["id"]
    with SessionFactory() as session:
        plan = session.get(ProductionPlan, UUID(plan_id))
        assert plan is not None
        legacy = {
            key: value
            for key, value in plan.request_payload.items()
            if key != "machine_assignments"
        }
        snapshot = {
            key: value
            for key, value in plan.snapshot.items()
            if key != "machine_assignments"
        }
        plan.request_payload = legacy
        plan.snapshot = snapshot
        session.commit()
    assert client.post(path, json=payload).json()["id"] == plan_id
    with SessionFactory() as session:
        plan = session.get(ProductionPlan, UUID(plan_id))
        assert plan is not None
        assert plan.request_payload == legacy
        assert plan.snapshot == snapshot


def test_multiple_steps_can_queue_on_the_same_machine(client: TestClient) -> None:
    recipe, variant = setup_recipe(client)
    selected = machine(client, "Compartida")
    assert (
        client.put(
            f"/api/v1/recipes/{recipe}/plan",
            json={
                "steps": [
                    {
                        "key": "first",
                        "title": "Primera impresión",
                        "task_type": "fdm_print",
                        "required_machine_type": "fdm_printer",
                    },
                    {
                        "key": "second",
                        "title": "Segunda impresión",
                        "task_type": "fdm_print",
                        "required_machine_type": "fdm_printer",
                        "output_variant_id": variant,
                        "depends_on": ["first"],
                    },
                ]
            },
        ).status_code
        == 200
    )
    order = create_order(client)
    payload = {
        "request_id": str(uuid4()),
        "recipe_id": recipe,
        "target_quantity": "1",
        "machine_assignments": {"first": selected, "second": selected},
    }
    response = client.post(f"/api/v1/orders/{order}/production-plans", json=payload)
    assert response.status_code == 201, response.text
    assert all(task["machine_id"] == selected for task in response.json()["tasks"])
    assert all(task["status"] == "queued" for task in response.json()["tasks"])
    with SessionFactory() as session:
        assert session.scalar(select(ProductionRun)) is None
