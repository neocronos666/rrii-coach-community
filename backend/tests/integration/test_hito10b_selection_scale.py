from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.integration import test_hito10b_options as catalog
from tests.integration.test_hito10b_base_recipe import final
from tests.integration.test_hito10b_configuration import selections
from tests.integration.test_hito10b_recipe_conditions import (
    condition,
    resolve,
    save,
    setup,
)
from tests.integration.test_production_api import create_order

pytestmark = pytest.mark.integration
client = catalog.client


@pytest.mark.parametrize("accessories,batches", [("2", "5"), ("3", "8")])
def test_scale_demand_not_yield_or_material(
    client: TestClient, accessories: str, batches: str
) -> None:
    product, variant, recipe, entry = setup(client)
    supply = client.post(
        "/api/v1/supplies",
        json={"name": "PLA", "category": "consumable", "base_unit": "g"},
    ).json()["id"]
    service = client.post("/api/v1/service-definitions", json={"name": "Lijar"})
    assert service.status_code == 201, service.text
    saved = save(
        client,
        recipe,
        [
            {
                "key": "print",
                "title": "Imprimir sombreros",
                "task_type": "fdm_print",
                "when_selected": condition(entry),
                "scale_by_selection": True,
                "batch_yield": "4",
                "supply_inputs": [{"supply_id": supply, "quantity_per_batch": "3"}],
            },
            {
                "key": "finish",
                "title": "Lijar por accesorio",
                "kind": "service",
                "service_definition_id": service.json()["id"],
                "when_selected": condition(entry),
                "scale_by_selection": True,
                "depends_on": ["print"],
            },
            {
                "key": "check",
                "title": "Revisar por producto",
                "kind": "service",
                "service_definition_id": service.json()["id"],
                "when_selected": condition(entry),
                "depends_on": ["finish"],
            },
            final(key="pack", depends_on=["check"]),
        ],
    )
    selected = [selections(entry, 1, accessories)]
    response = resolve(client, product, variant, quantity="10", selections=selected)
    assert response.status_code == 200, response.text
    calculated = {step["key"]: step for step in response.json()["planned_steps"]}
    assert Decimal(calculated["print"]["required_quantity"]) == 10 * Decimal(
        accessories
    )
    assert Decimal(calculated["finish"]["required_quantity"]) == 10 * Decimal(
        accessories
    )
    assert Decimal(calculated["check"]["required_quantity"]) == 10
    assert Decimal(calculated["pack"]["required_quantity"]) == 10
    assert Decimal(calculated["print"]["batches"]) == Decimal(batches)
    resolved = response.json()["plan"]["steps"][0]
    assert Decimal(resolved["batch_yield"]) == 4
    assert Decimal(resolved["supply_inputs"][0]["quantity_per_batch"]) == 3
    order = create_order(client)
    path = f"/api/v1/orders/{order}/production-plans"
    payload = {
        "request_id": str(uuid4()),
        "recipe_id": recipe,
        "variant_id": variant,
        "target_quantity": "10",
        "selections": selected,
    }
    created = client.post(path, json=payload)
    assert created.status_code == 201, created.text
    task = next(
        task for task in created.json()["tasks"] if task["recipe_step_key"] == "print"
    )
    reservations = client.get(
        f"/api/v1/production-tasks/{task['id']}/supply-reservations"
    ).json()
    assert Decimal(reservations[0]["quantity"]) == Decimal(batches) * 3
    assert client.get(f"/api/v1/recipes/{recipe}/plan").json() == saved
    save(client, recipe, [final()])
    retry = client.post(path, json=payload)
    assert retry.status_code == 201
    assert retry.json()["snapshot"] == created.json()["snapshot"]


@pytest.mark.parametrize(
    "step",
    [
        {"key": "a", "title": "Sin selección", "scale_by_selection": True},
        final(scale_by_selection=True),
    ],
)
def test_invalid_scale_is_atomic(client: TestClient, step: dict[str, Any]) -> None:
    _product, _variant, recipe, entry = setup(client)
    saved = save(client, recipe, [final()])
    if step.get("is_final_output"):
        step = {**step, "when_selected": condition(entry)}
    response = client.put(f"/api/v1/recipes/{recipe}/plan", json={"steps": [step]})
    assert response.status_code == 422
    assert client.get(f"/api/v1/recipes/{recipe}/plan").json() == saved


@pytest.mark.parametrize(
    "factor,selected", [("999999999999", "2"), ("0.000001", "0.000001")]
)
def test_scale_range_and_precision_rejected(
    client: TestClient, factor: str, selected: str
) -> None:
    product, variant, recipe, entry = setup(client)
    save(
        client,
        recipe,
        [
            {
                "key": "piece",
                "title": "Pieza",
                "when_selected": condition(entry),
                "scale_by_selection": True,
                "quantity_per_output": factor,
            },
            final(depends_on=["piece"]),
        ],
    )
    response = resolve(
        client, product, variant, selections=[selections(entry, 1, selected)]
    )
    assert response.status_code == 409, response.text


def test_unselected_scaled_step_is_omitted(client: TestClient) -> None:
    product, variant, recipe, entry = setup(client)
    save(
        client,
        recipe,
        [
            {
                "key": "piece",
                "title": "Pieza",
                "when_selected": condition(entry),
                "scale_by_selection": True,
            },
            final(depends_on=["piece"]),
        ],
    )
    response = resolve(client, product, variant)
    assert response.status_code == 200, response.text
    assert response.json()["omitted_step_keys"] == ["piece"]
    assert response.json()["plan"]["steps"][0]["depends_on"] == []
