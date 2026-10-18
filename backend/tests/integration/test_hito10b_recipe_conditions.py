from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.session import SessionFactory
from app.modules.production.plan_models import ProductionPlan
from app.modules.recipes.resolution import RecipeResolutionService, RecipeResolveInput
from app.modules.recipes.schemas import PlanRead, RecipePlan
from tests.integration import test_hito10b_options as catalog
from tests.integration.test_hito10b_base_recipe import base, final, product
from tests.integration.test_hito10b_configuration import configure, option, selections
from tests.integration.test_production_api import create_order

pytestmark = pytest.mark.integration
client = catalog.client


def setup(client: TestClient) -> tuple[str, str, str, dict[str, Any]]:
    product_id, variant = product(client)
    recipe = base(client, product_id)
    entry = option(client, "Pintura", 1)
    configure(client, product_id, [entry])
    return product_id, variant, recipe, entry


def condition(entry: dict[str, Any]) -> dict[str, str]:
    return {
        "definition_id": entry["definition_id"],
        "value_id": entry["values"][0]["value_id"],
    }


def save(
    client: TestClient, recipe: str, steps: list[dict[str, Any]]
) -> dict[str, Any]:
    response = client.put(f"/api/v1/recipes/{recipe}/plan", json={"steps": steps})
    assert response.status_code == 200, response.text
    return dict(response.json())


def resolve(client: TestClient, product_id: str, variant: str, **changes: Any) -> Any:
    return client.post(
        f"/api/v1/products/{product_id}/recipe/resolve",
        json={"variant_id": variant, "quantity": "3", **changes},
    )


def steps(entry: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"key": "print", "title": "Imprimir", "task_type": "fdm_print"},
        {
            "key": "paint",
            "title": "Pintar",
            "when_selected": condition(entry),
            "depends_on": ["print"],
        },
        {
            "key": "dry",
            "title": "Dejar secar",
            "kind": "wait",
            "when_selected": condition(entry),
            "depends_on": ["paint"],
        },
        {"key": "box", "title": "Preparar caja"},
        final(key="pack", title="Empaquetar", depends_on=["dry", "box"]),
    ]


def test_optional_chain_join_defaults_and_no_persistence(client: TestClient) -> None:
    product_id, variant, recipe, entry = setup(client)
    saved = save(client, recipe, steps(entry))
    for count, omitted, dependencies in [
        (0, ["dry", "paint"], ["box", "print"]),
        (1, [], ["box", "dry"]),
    ]:
        response = resolve(
            client, product_id, variant, selections=[selections(entry, count, "2")]
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["omitted_step_keys"] == omitted
        assert result["plan"]["steps"][-1]["depends_on"] == dependencies
        assert result["plan"]["steps"][-1]["output_variant_id"] == variant
        assert {item["required_quantity"] for item in result["planned_steps"]} == {
            "3.000000"
        }
        assert (
            resolve(
                client, product_id, variant, selections=[selections(entry, count, "2")]
            ).json()
            == result
        )
    entry["values"][0]["default_quantity"] = "1"
    configure(client, product_id, [entry])
    assert resolve(client, product_id, variant).json()["omitted_step_keys"] == []
    assert resolve(
        client, product_id, variant, selections=[selections(entry, 0)]
    ).json()["omitted_step_keys"] == ["dry", "paint"]
    assert client.get(f"/api/v1/recipes/{recipe}/plan").json() == saved
    with SessionFactory() as session:
        assert session.scalar(select(func.count()).select_from(ProductionPlan)) == 0


def test_missing_physical_supplier_is_not_replaced_by_stock(client: TestClient) -> None:
    product_id, variant, recipe, entry = setup(client)
    _, intermediate = product(client)
    save(
        client,
        recipe,
        [
            {
                "key": "piece",
                "title": "Pieza",
                "output_variant_id": intermediate,
                "when_selected": condition(entry),
            },
            final(
                depends_on=["piece"],
                product_inputs=[
                    {
                        "product_variant_id": intermediate,
                        "quantity_per_batch": "1",
                        "source_step_key": "piece",
                    }
                ],
            ),
        ],
    )
    missing = resolve(client, product_id, variant)
    assert missing.status_code == 409
    assert "proveedor físico" in missing.json()["detail"]
    assert (
        resolve(
            client, product_id, variant, selections=[selections(entry, 1)]
        ).status_code
        == 200
    )


def test_invalid_condition_and_changed_configuration(client: TestClient) -> None:
    product_id, variant, recipe, entry = setup(client)
    saved = save(client, recipe, steps(entry))
    invalid = steps(entry)
    invalid[1]["when_selected"]["value_id"] = str(uuid4())
    response = client.put(f"/api/v1/recipes/{recipe}/plan", json={"steps": invalid})
    assert response.status_code == 409
    assert client.get(f"/api/v1/recipes/{recipe}/plan").json() == saved
    configure(client, product_id, [])
    assert resolve(client, product_id, variant).status_code == 409
    configure(client, product_id, [entry])
    assert resolve(client, product_id, variant).status_code == 200


@pytest.mark.parametrize(
    "changes,status",
    [
        ({"quantity": "1.5"}, 409),
        ({"quantity": "0"}, 422),
        ({"quantity": "NaN"}, 422),
        ({"variant_id": str(uuid4())}, 404),
    ],
)
def test_resolve_quantity_and_variant(
    client: TestClient, changes: dict[str, Any], status: int
) -> None:
    product_id, variant, recipe, entry = setup(client)
    save(client, recipe, steps(entry))
    assert resolve(client, product_id, variant, **changes).status_code == status


def test_final_output_cannot_disappear(client: TestClient) -> None:
    product_id, variant, recipe, entry = setup(client)
    save(client, recipe, [final(when_selected=condition(entry))])
    assert resolve(client, product_id, variant).status_code == 409
    assert (
        resolve(
            client, product_id, variant, selections=[selections(entry, 1)]
        ).status_code
        == 200
    )


def test_legacy_plan_retries_preserved_after_recipe_becomes_conditional(
    client: TestClient,
) -> None:
    _product_id, variant, recipe, entry = setup(client)
    save(client, recipe, [final()])
    order = create_order(client)
    path = f"/api/v1/orders/{order}/production-plans"
    payload = {
        "request_id": str(uuid4()),
        "recipe_id": recipe,
        "variant_id": variant,
        "target_quantity": "3",
    }
    created = client.post(path, json=payload)
    assert created.status_code == 201, created.text
    save(client, recipe, steps(entry))
    retry = client.post(path, json=payload)
    assert retry.status_code in (200, 201), retry.text
    assert retry.json()["snapshot"] == created.json()["snapshot"]
    assert (
        client.post(path, json={**payload, "request_id": str(uuid4())}).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/recipes/{recipe}/production-preview",
            json={"variant_id": variant, "target_quantity": "3"},
        ).status_code
        == 200
    )


def test_resolve_keeps_one_snapshot_during_recipe_edit(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    product_id, variant, recipe, entry = setup(client)
    saved = save(client, recipe, steps(entry))
    with SessionFactory() as session:
        service = RecipeResolutionService(session)
        original = service.recipes.plan

        def concurrent_edit(recipe_id: UUID) -> PlanRead:
            save(client, recipe, [final(title="Otra receta")])
            return original(recipe_id)

        monkeypatch.setattr(service.recipes, "plan", concurrent_edit)
        result = service.resolve(
            UUID(product_id),
            RecipeResolveInput(variant_id=UUID(variant), quantity=Decimal("3")),
        )
        assert [step.key for step in result.plan.steps] == ["print", "box", "pack"]
        RecipePlan(steps=list(result.plan.steps))
    assert client.get(f"/api/v1/recipes/{recipe}/plan").json() != saved


def test_conditions_reject_foreign_product_and_legacy_recipe(
    client: TestClient,
) -> None:
    product_id, variant, recipe, entry = setup(client)
    saved = save(client, recipe, [final()])
    other = option(client, "Ajena", 1)
    response = client.put(
        f"/api/v1/recipes/{recipe}/plan",
        json={"steps": [final(when_selected=condition(other))]},
    )
    assert response.status_code == 409
    assert client.get(f"/api/v1/recipes/{recipe}/plan").json() == saved
    legacy = client.post(
        f"/api/v1/product-variants/{variant}/recipes", json={"name": "Heredada"}
    ).json()["id"]
    assert (
        client.put(
            f"/api/v1/recipes/{legacy}/plan",
            json={
                "steps": [
                    final(
                        is_final_output=False,
                        output_variant_id=variant,
                        when_selected=condition(entry),
                    )
                ]
            },
        ).status_code
        == 409
    )
    assert (
        resolve(
            client, product_id, variant, selections=[selections(other, 1)]
        ).status_code
        == 409
    )


def test_unconditional_continuous_quantity_and_foreign_variant(
    client: TestClient,
) -> None:
    product_id, variant, recipe, _entry = setup(client)
    continuous = client.post(
        f"/api/v1/products/{product_id}/variants",
        json={"name": "Longitud", "base_unit": "m"},
    ).json()["id"]
    save(client, recipe, [final(unit="m")])
    response = resolve(client, product_id, continuous, quantity="1.25")
    assert response.status_code == 200, response.text
    assert response.json()["planned_steps"][0]["required_quantity"] == "1.250000"
    assert resolve(client, product_id, variant).status_code == 409
    _, foreign = product(client)
    assert resolve(client, product_id, foreign).status_code == 409


def test_conditional_resources_preserved_only_on_active_step(
    client: TestClient,
) -> None:
    from tests.integration.test_hito10b_recipe_resources import asset, resource

    product_id, variant, recipe, entry = setup(client)
    item = asset(client)
    recipe_steps = steps(entry)
    recipe_steps[1]["resources"] = [
        resource(item["current_revision_id"], quantity_per_batch="2.5")
    ]
    recipe_steps[1]["instructions"] = "Pintar con esponja"
    saved = save(client, recipe, recipe_steps)
    active = resolve(client, product_id, variant, selections=[selections(entry, 1)])
    assert active.status_code == 200, active.text
    assert active.json()["plan"]["steps"][1] == saved["steps"][1]
    inactive = resolve(client, product_id, variant).json()
    assert all(not step["resources"] for step in inactive["plan"]["steps"])
