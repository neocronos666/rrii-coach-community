from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionFactory
from app.modules.recipes.resolution import RecipeResolutionService, RecipeResolveInput
from app.modules.recipes.schemas import PlanRead
from tests.integration import test_hito10b_options as catalog
from tests.integration.test_hito10b_base_recipe import final
from tests.integration.test_hito10b_configuration import (
    configure,
    physical_value,
    selections,
)
from tests.integration.test_hito10b_recipe_conditions import (
    condition,
    resolve,
    save,
    setup,
)
from tests.integration.test_hito10b_recipe_resources import resource
from tests.integration.test_hito10b_recipe_steps import service, service_step
from tests.integration.test_hito10b_selection_resources import dynamic
from tests.integration.test_production_api import create_order

pytestmark = pytest.mark.integration
client = catalog.client


def test_automatic_context_keeps_one_snapshot_during_catalog_changes(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    product, variant, recipe, entry = setup(client)
    asset = physical_value(client, entry, 0, "Gaucho")
    entry["values"][0]["default_quantity"] = "1"
    configure(client, product, [entry])
    definition = service(client)
    assert (
        client.patch(
            f"/api/v1/service-definitions/{definition}",
            json={
                "action_template": "{product}: {quantity} {piece}",
            },
        ).status_code
        == 200
    )
    save(
        client,
        recipe,
        [
            service_step(
                definition,
                action_context={},
                resources=[dynamic(entry)],
            ),
            final(),
        ],
    )
    with SessionFactory() as session:
        resolver = RecipeResolutionService(session)
        original = resolver.recipes.plan

        def concurrent_change(recipe_id: UUID) -> PlanRead:
            assert (
                client.patch(
                    f"/api/v1/products/{product}",
                    json={
                        "name": "Nuevo producto",
                    },
                ).status_code
                == 200
            )
            assert (
                client.patch(
                    f"/api/v1/assets/{asset['id']}",
                    json={
                        "name": "Nuevo diseño",
                    },
                ).status_code
                == 200
            )
            assert (
                client.patch(
                    f"/api/v1/service-definitions/{definition}",
                    json={
                        "action_template": "Nuevo {product}: {quantity} {piece}",
                    },
                ).status_code
                == 200
            )
            return original(recipe_id)

        monkeypatch.setattr(resolver.recipes, "plan", concurrent_change)
        result = resolver.resolve(
            UUID(product),
            RecipeResolveInput(
                variant_id=UUID(variant),
                quantity=Decimal("3"),
            ),
        )
        assert result.plan.steps[0].service_action == "Figura: 3 Gaucho"
    current = resolve(client, product, variant)
    assert current.status_code == 200, current.text
    assert current.json()["plan"]["steps"][0]["service_action"] == (
        "Nuevo Nuevo producto: 3 Nuevo diseño"
    )


@pytest.mark.parametrize("fixed", [False, True])
def test_resource_labels_and_decimal_demand_are_resolved_without_mutating_recipe(
    client: TestClient, fixed: bool
) -> None:
    product, variant, recipe, entry = setup(client)
    asset = physical_value(client, entry, 0, "Gaucho {product}")
    entry["values"][0]["default_quantity"] = "2"
    configure(client, product, [entry])
    reference = resource(asset["current_revision_id"]) if fixed else dynamic(entry)
    reference.update(label="Sombrero", quantity_per_batch="7")
    saved = save(
        client,
        recipe,
        [
            service_step(
                service(client),
                action_context={},
                action_template="{product}: {quantity} {piece} de {design}",
                resources=[reference],
                quantity_per_output="0.125",
                batch_yield="4",
                when_selected=condition(entry),
                scale_by_selection=True,
            ),
            final(depends_on=["sand"]),
        ],
    )
    assert saved["steps"][0]["service_action"] is None
    assert saved["steps"][0]["action_context"] == {}
    response = resolve(client, product, variant, quantity="3")
    assert response.status_code == 200, response.text
    step = response.json()["plan"]["steps"][0]
    assert step["service_action"] == "Figura: 0.75 Sombrero de Gaucho {product}"
    assert step["action_context"] == {
        "product": "Figura",
        "quantity": "0.75",
        "piece": "Sombrero",
        "design": "Gaucho {product}",
    }
    assert client.get(f"/api/v1/recipes/{recipe}/plan").json() == saved


def test_explicit_context_wins_and_does_not_change_demand(client: TestClient) -> None:
    product, variant, recipe, _ = setup(client)
    save(
        client,
        recipe,
        [
            service_step(
                service(client),
                action_template="{quantity} {piece} para {product}",
                action_context={"quantity": "muchas", "piece": "pieza explícita"},
            ),
            final(depends_on=["sand"]),
        ],
    )
    response = resolve(client, product, variant, quantity="10")
    assert response.status_code == 200, response.text
    assert response.json()["plan"]["steps"][0]["service_action"] == (
        "muchas pieza explícita para Figura"
    )
    assert response.json()["planned_steps"][0]["required_quantity"] == "10.000000"


@pytest.mark.parametrize("count", [0, 2])
def test_missing_or_ambiguous_resource_rejects_save_atomically(
    client: TestClient, count: int
) -> None:
    product, variant, recipe, entry = setup(client)
    asset = physical_value(client, entry, 0, "Gaucho")
    previous = save(client, recipe, [final()])
    refs = [
        resource(asset["current_revision_id"], key=f"part{i}") for i in range(count)
    ]
    response = client.put(
        f"/api/v1/recipes/{recipe}/plan",
        json={
            "steps": [
                service_step(service(client), action_context={}, resources=refs),
                final(),
            ]
        },
    )
    assert response.status_code == 409, response.text
    assert client.get(f"/api/v1/recipes/{recipe}/plan").json() == previous
    assert resolve(client, product, variant).status_code == 200


def test_omitted_service_needs_no_selected_resource_and_active_failure_is_atomic(
    client: TestClient,
) -> None:
    product, variant, recipe, entry = setup(client)
    definition = service(client)
    save(
        client,
        recipe,
        [
            service_step(
                definition,
                action_context={},
                when_selected=condition(entry),
                resources=[dynamic(entry)],
            ),
            final(depends_on=["sand"]),
        ],
    )
    omitted = resolve(client, product, variant)
    assert omitted.status_code == 200, omitted.text
    assert omitted.json()["omitted_step_keys"] == ["sand"]
    assert omitted.json()["plan"]["steps"][0]["depends_on"] == []
    choice = [selections(entry, 1)]
    assert resolve(client, product, variant, selections=choice).status_code == 409
    order = create_order(client)
    request = {
        "recipe_id": recipe,
        "variant_id": variant,
        "target_quantity": "3",
        "request_id": str(uuid4()),
        "selections": choice,
    }
    endpoint = f"/api/v1/orders/{order}/production-plans"
    assert client.post(endpoint, json=request).status_code == 409
    physical_value(client, entry, 0, "Gaucho")
    created = client.post(endpoint, json=request)
    assert created.status_code == 201, created.text
    task = next(t for t in created.json()["tasks"] if t["recipe_step_key"] == "sand")
    assert task["description"].startswith("Lijar Gaucho")


def test_multiple_resources_allowed_with_explicit_piece_and_design(
    client: TestClient,
) -> None:
    product, variant, recipe, entry = setup(client)
    asset = physical_value(client, entry, 0, "Gaucho")
    save(
        client,
        recipe,
        [
            service_step(
                service(client),
                action_template="{piece} {design}: {quantity}",
                action_context={"piece": "conjunto", "design": "especial"},
                resources=[
                    resource(asset["current_revision_id"], key=f"r{i}")
                    for i in range(2)
                ],
            ),
            final(),
        ],
    )
    response = resolve(client, product, variant)
    assert response.status_code == 200, response.text
    assert (
        response.json()["plan"]["steps"][0]["service_action"] == "conjunto especial: 3"
    )


def test_catalog_template_change_uses_current_automatic_context(
    client: TestClient,
) -> None:
    product, variant, recipe, _ = setup(client)
    definition = service(client)
    save(client, recipe, [service_step(definition), final()])
    assert (
        client.patch(
            f"/api/v1/service-definitions/{definition}",
            json={
                "action_template": "{product}: {quantity} {piece}",
            },
        ).status_code
        == 200
    )
    assert (
        client.get(f"/api/v1/recipes/{recipe}/plan").json()["steps"][0][
            "service_action"
        ]
        is None
    )
    response = resolve(client, product, variant)
    assert response.status_code == 200, response.text
    assert response.json()["plan"]["steps"][0]["service_action"] == (
        "Figura: 3 brazo derecho de Hulk"
    )
