from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.integration import test_hito10b_options as catalog_tests
from tests.integration.test_hito9_recipes import setup_recipe
from tests.integration.test_production_api import create_order

pytestmark = pytest.mark.integration
client = catalog_tests.client


def service(client: TestClient) -> str:
    response = client.post(
        "/api/v1/service-definitions",
        json={
            "name": "Lijado",
            "action_template": "Lijar {piece}",
            "instructions": "Usar lija fina.",
        },
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def service_step(definition: str, key: str = "sand", **changes: Any) -> dict[str, Any]:
    return {
        "key": key,
        "title": key,
        "kind": "service",
        "service_definition_id": definition,
        "action_context": {"piece": "brazo derecho de Hulk"},
        **changes,
    }


def test_reusable_services_parallel_branches_join_and_text_wait(
    client: TestClient,
) -> None:
    recipe, _ = setup_recipe(client)
    definition = service(client)
    body = {
        "steps": [
            service_step(definition, "arm"),
            service_step(
                definition,
                "hair",
                action_context={"piece": "cabello de Goku"},
                action_template="Pulir {piece}",
            ),
            {
                "key": "dry",
                "title": "Dejar secar 10 min",
                "kind": "wait",
                "depends_on": ["arm", "hair"],
            },
            {"key": "pack", "title": "Empaquetar", "depends_on": ["dry"]},
        ]
    }
    path = f"/api/v1/recipes/{recipe}/plan"
    response = client.put(path, json=body)
    assert response.status_code == 200, response.text
    saved = response.json()
    assert client.get(path).json() == saved
    arm, hair, dry, pack = saved["steps"]
    assert arm["service_definition_id"] == hair["service_definition_id"] == definition
    assert arm["service_action"] == "Lijar brazo derecho de Hulk"
    assert hair["service_action"] == "Pulir cabello de Goku"
    assert arm["service_instructions"] == "Usar lija fina."
    assert dry["kind"] == "wait"
    assert dry["depends_on"] == ["arm", "hair"]
    assert dry["parameters"] == {}
    assert pack["kind"] == "operation"
    assert pack["service_action"] is None
    body["steps"][0]["depends_on"] = ["pack"]
    assert client.put(path, json=body).status_code == 422
    assert client.get(path).json() == saved


@pytest.mark.parametrize("task_type", ["fdm_print", "sla_print", "cnc", "manual"])
def test_legacy_step_kind_inferred_without_changing_technology(
    client: TestClient, task_type: str
) -> None:
    recipe, _ = setup_recipe(client)
    response = client.put(
        f"/api/v1/recipes/{recipe}/plan",
        json={
            "steps": [
                {"key": "make", "title": "Fabricar", "task_type": task_type},
            ]
        },
    )
    assert response.status_code == 200, response.text
    saved = response.json()["steps"][0]
    assert saved["task_type"] == task_type
    assert saved["kind"] == ("print" if task_type.endswith("_print") else "operation")


@pytest.mark.parametrize(
    "changes",
    [
        {"service_definition_id": None},
        {"kind": "operation"},
        {"task_type": "fdm_print"},
        {"task_type": "laser"},
        {"suggested_machine_id": str(uuid4())},
        {"required_machine_type": "fdm"},
        {"action_context": {"unknown": "x"}},
        {"action_template": "Lijar {piece.name}"},
        {"service_action": "Texto enviado por cliente"},
    ],
)
def test_invalid_service_payload_preserves_recipe(
    client: TestClient, changes: dict[str, Any]
) -> None:
    recipe, _ = setup_recipe(client)
    definition = service(client)
    path = f"/api/v1/recipes/{recipe}/plan"
    valid = {"steps": [service_step(definition)]}
    previous = client.put(path, json=valid)
    assert previous.status_code == 200
    assert (
        client.put(
            path, json={"steps": [service_step(definition, **changes)]}
        ).status_code
        == 422
    )
    assert client.get(path).json() == previous.json()


@pytest.mark.parametrize(
    "changes",
    [
        {"output_variant_id": str(uuid4())},
        {"parameters": {"duration_minutes": 10}},
        {"duration_minutes": 10},
        {"supply_inputs": [{"supply_id": str(uuid4()), "quantity_per_batch": "1"}]},
        {"task_type": "assembly"},
        {"action_template": "Esperar"},
        {"kind": "print"},
    ],
)
def test_wait_is_text_without_manufacturing_payload(
    client: TestClient, changes: dict[str, Any]
) -> None:
    recipe, _ = setup_recipe(client)
    response = client.put(
        f"/api/v1/recipes/{recipe}/plan",
        json={
            "steps": [
                {"key": "dry", "title": "Dejar secar", "kind": "wait", **changes},
            ]
        },
    )
    assert response.status_code == 422, response.text


def test_missing_inactive_and_incomplete_service_references_are_atomic(
    client: TestClient,
) -> None:
    recipe, _ = setup_recipe(client)
    definition = service(client)
    path = f"/api/v1/recipes/{recipe}/plan"
    previous = client.put(path, json={"steps": [service_step(definition)]}).json()
    for payload in (
        service_step(str(uuid4())),
        service_step(definition, action_context={}),
    ):
        assert client.put(path, json={"steps": [payload]}).status_code == 409
        assert client.get(path).json() == previous
    assert (
        client.patch(
            f"/api/v1/service-definitions/{definition}", json={"active": False}
        ).status_code
        == 200
    )
    assert (
        client.put(path, json={"steps": [service_step(definition)]}).status_code == 409
    )
    assert client.get(path).json() == previous


def test_service_without_template_uses_name(client: TestClient) -> None:
    recipe, _ = setup_recipe(client)
    definition = client.post(
        "/api/v1/service-definitions", json={"name": "Ensamblar"}
    ).json()["id"]
    response = client.put(
        f"/api/v1/recipes/{recipe}/plan",
        json={
            "steps": [
                service_step(definition, action_context={}),
            ]
        },
    )
    assert response.status_code == 200
    assert response.json()["steps"][0]["service_action"] == "Ensamblar"


def test_production_freezes_service_text_and_dag_after_catalog_and_recipe_changes(
    client: TestClient,
) -> None:
    recipe, variant = setup_recipe(client)
    definition = service(client)
    path = f"/api/v1/recipes/{recipe}/plan"
    body = {
        "steps": [
            service_step(
                definition, "left", action_context={"piece": "brazo izquierdo"}
            ),
            service_step(
                definition, "right", action_context={"piece": "brazo derecho"}
            ),
            {
                "key": "dry",
                "title": "Dejar secar",
                "kind": "wait",
                "depends_on": ["left", "right"],
            },
            service_step(
                definition,
                "finish",
                depends_on=["dry"],
                output_variant_id=variant,
                instructions="Revisar las uniones.",
            ),
        ]
    }
    assert client.put(path, json=body).status_code == 200
    order = create_order(client)
    request = {"request_id": str(uuid4()), "recipe_id": recipe, "target_quantity": "2"}
    endpoint = f"/api/v1/orders/{order}/production-plans"
    response = client.post(endpoint, json=request)
    assert response.status_code == 201, response.text
    plan = response.json()
    tasks = {task["recipe_step_key"]: task for task in plan["tasks"]}
    assert tasks["left"]["description"] == "Lijar brazo izquierdo\n\nUsar lija fina."
    assert tasks["finish"]["description"].endswith("\n\nRevisar las uniones.")
    assert tasks["dry"]["recipe_snapshot"]["step"]["kind"] == "wait"
    assert tasks["dry"]["recipe_snapshot"]["step"]["depends_on"] == ["left", "right"]
    assert (
        client.patch(
            f"/api/v1/service-definitions/{definition}",
            json={
                "name": "Pulido",
                "action_template": "Pulir {piece}",
                "instructions": "Otra técnica.",
            },
        ).status_code
        == 200
    )
    assert (
        client.get(path).json()["steps"][0]["service_action"] == "Pulir brazo izquierdo"
    )
    # Un cambio de plantilla puede exigir contexto nuevo; nunca altera históricos.
    assert (
        client.patch(
            f"/api/v1/service-definitions/{definition}",
            json={"action_template": "Pulir {piece} de {product}"},
        ).status_code
        == 200
    )
    assert client.get(path).status_code == 409
    assert (
        client.get(f"/api/v1/production-plans/{plan['id']}").json()["snapshot"]
        == plan["snapshot"]
    )
    assert client.post(endpoint, json=request).json()["id"] == plan["id"]
    assert (
        client.put(
            path,
            json={
                "steps": [
                    {
                        "key": "new",
                        "title": "Nueva receta",
                        "output_variant_id": variant,
                    }
                ]
            },
        ).status_code
        == 200
    )
    historical = client.get(f"/api/v1/production-plans/{plan['id']}").json()
    assert historical["snapshot"] == plan["snapshot"]
    assert historical["tasks"] == plan["tasks"]
    assert client.post(endpoint, json=request).json()["id"] == plan["id"]
