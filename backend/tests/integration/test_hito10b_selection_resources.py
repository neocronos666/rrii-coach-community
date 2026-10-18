from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionFactory
from app.modules.assets.models import AssetRevision
from app.modules.production.models import ProductionTaskAssetRevision
from tests.integration import test_hito10b_options as catalog
from tests.integration.test_hito10b_base_recipe import final
from tests.integration.test_hito10b_configuration import (
    configure,
    option,
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
from tests.integration.test_production_api import create_order

pytestmark = pytest.mark.integration
client = catalog.client


def dynamic(entry: dict[str, Any], **changes: Any) -> dict[str, Any]:
    return {"key": "hat", "from_selection": condition(entry), **changes}


def test_dynamic_resource_defaults_scale_snapshot_and_historical_fk(
    client: TestClient,
) -> None:
    product, variant, recipe, entry = setup(client)
    item = physical_value(client, entry, 0, "Gaucho")
    pinned = item["current_revision_id"]
    entry["values"][0]["default_quantity"] = "2"
    configure(client, product, [entry])
    saved = save(
        client,
        recipe,
        [
            {
                "key": "hat",
                "title": "Sombrero",
                "when_selected": condition(entry),
                "scale_by_selection": True,
                "batch_yield": "4",
                "resources": [dynamic(entry, quantity_per_batch="3", label="Gaucho")],
            },
            final(resources=[resource(pinned)], depends_on=["hat"]),
        ],
    )
    assert saved["steps"][0]["resources"][0]["from_selection"] == condition(entry)
    response = resolve(client, product, variant, quantity="10")
    assert response.status_code == 200, response.text
    resolved = response.json()["plan"]["steps"][0]["resources"][0]
    assert resolved["asset_revision_id"] == pinned
    assert resolved["asset_id"] == item["id"]
    assert resolved["label"] == "Gaucho"
    assert Decimal(resolved["quantity_per_batch"]) == 3
    assert Decimal(response.json()["planned_steps"][0]["required_quantity"]) == 20
    assert client.get(f"/api/v1/recipes/{recipe}/plan").json() == saved
    preview = client.post(
        f"/api/v1/recipes/{recipe}/production-preview",
        json={"variant_id": variant, "target_quantity": "10"},
    )
    assert preview.status_code == 200, preview.text
    order = create_order(client)
    endpoint = f"/api/v1/orders/{order}/production-plans"
    payload = {
        "request_id": str(uuid4()),
        "recipe_id": recipe,
        "variant_id": variant,
        "target_quantity": "10",
    }
    created = client.post(endpoint, json=payload)
    assert created.status_code == 201, created.text
    task = next(t for t in created.json()["tasks"] if t["recipe_step_key"] == "hat")
    assert task["recipe_snapshot"]["step"]["resources"][0] == resolved
    revised = client.post(f"/api/v1/assets/{item['id']}/revisions", json={})
    assert revised.status_code == 201
    current = resolve(client, product, variant).json()
    assert (
        current["plan"]["steps"][0]["resources"][0]["asset_revision_id"]
        == revised.json()["id"]
    )
    save(client, recipe, [final()])
    configure(client, product, [])
    retry = client.post(endpoint, json=payload)
    assert retry.status_code == 201
    assert retry.json()["snapshot"] == created.json()["snapshot"]
    assert retry.json()["tasks"] == created.json()["tasks"]
    with SessionFactory() as session:
        refs = session.scalars(
            select(ProductionTaskAssetRevision).where(
                ProductionTaskAssetRevision.task_id == UUID(task["id"])
            )
        ).all()
        assert [str(ref.asset_revision_id) for ref in refs] == [pinned]
        with pytest.raises(IntegrityError) as error:
            session.execute(
                delete(AssetRevision).where(AssetRevision.id == UUID(pinned))
            )
        assert "production_task_asset_revisions" in str(error.value.orig)
        session.rollback()


def test_active_resource_requires_selected_physical_value(client: TestClient) -> None:
    product, variant, recipe, entry = setup(client)
    save(client, recipe, [final(resources=[dynamic(entry)])])
    for count in (0, 1):
        response = resolve(
            client, product, variant, selections=[selections(entry, count)]
        )
        assert response.status_code == 409
        assert "implementación física" in response.json()["detail"]
    physical_value(client, entry, 0, "Gaucho")
    assert (
        resolve(client, product, variant, selections=[selections(entry, 1)]).status_code
        == 200
    )


def test_omitted_step_needs_no_physical_resource_and_reconnects(
    client: TestClient,
) -> None:
    product, variant, recipe, entry = setup(client)
    save(
        client,
        recipe,
        [
            {"key": "start", "title": "Preparar"},
            {
                "key": "hat",
                "title": "Sombrero",
                "when_selected": condition(entry),
                "resources": [dynamic(entry)],
                "depends_on": ["start"],
            },
            final(depends_on=["hat"]),
        ],
    )
    response = resolve(client, product, variant, selections=[selections(entry, 0)])
    assert response.status_code == 200, response.text
    assert response.json()["omitted_step_keys"] == ["hat"]
    assert response.json()["plan"]["steps"][-1]["depends_on"] == ["start"]


@pytest.mark.parametrize("invalid", ["both", "neither", "foreign", "duplicate"])
def test_invalid_sources_are_atomic(client: TestClient, invalid: str) -> None:
    _product, _variant, recipe, entry = setup(client)
    item = physical_value(client, entry, 0, "Gaucho")
    saved = save(client, recipe, [final()])
    resources = [dynamic(entry)]
    expected = 422
    if invalid == "both":
        resources[0]["asset_revision_id"] = item["current_revision_id"]
    elif invalid == "neither":
        resources = [{"key": "hat"}]
    elif invalid == "foreign":
        resources[0]["from_selection"]["value_id"] = str(uuid4())
        expected = 409
    else:
        resources.append(resource(item["current_revision_id"], key="hat"))
    response = client.put(
        f"/api/v1/recipes/{recipe}/plan", json={"steps": [final(resources=resources)]}
    )
    assert response.status_code == expected, response.text
    assert client.get(f"/api/v1/recipes/{recipe}/plan").json() == saved


def test_removed_option_and_legacy_recipe_rejected(client: TestClient) -> None:
    product, variant, recipe, entry = setup(client)
    physical_value(client, entry, 0, "Gaucho")
    save(client, recipe, [final(resources=[dynamic(entry)])])
    configure(client, product, [])
    assert resolve(client, product, variant).status_code == 409
    legacy = client.post(
        f"/api/v1/product-variants/{variant}/recipes", json={"name": "Heredada"}
    ).json()["id"]
    response = client.put(
        f"/api/v1/recipes/{legacy}/plan",
        json={
            "steps": [
                {
                    "key": "make",
                    "title": "Fabricar",
                    "output_variant_id": variant,
                    "resources": [dynamic(entry)],
                }
            ]
        },
    )
    assert response.status_code == 409


def test_context_selects_adaptation_and_reports_missing_or_ambiguous(
    client: TestClient,
) -> None:
    product, variant, recipe, hat = setup(client)
    heads = option(client, "Cabezas", 2)
    first = physical_value(client, heads, 0, "Pikachu")
    second = physical_value(client, heads, 1, "Raichu")
    gaucho = physical_value(client, hat, 0, "Gaucho Pikachu")
    other = client.post(
        "/api/v1/assets",
        json={"name": "Gaucho Raichu", "family_id": gaucho["family_id"]},
    ).json()
    for target, adaptation in ((first, gaucho), (second, other)):
        assert (
            client.put(
                f"/api/v1/assets/{target['id']}/compatibilities/{adaptation['id']}"
            ).status_code
            == 200
        )
    hat["context_definition_id"] = heads["definition_id"]
    configure(client, product, [hat, heads])
    save(client, recipe, [final(resources=[dynamic(hat)])])
    for index, expected in ((0, gaucho), (1, other)):
        selected = [
            selections(hat, 1),
            {
                "definition_id": heads["definition_id"],
                "values": [heads["values"][index]],
            },
        ]
        response = resolve(client, product, variant, selections=selected)
        assert response.status_code == 200, response.text
        assert (
            response.json()["plan"]["steps"][0]["resources"][0]["asset_id"]
            == expected["id"]
        )
    assert (
        client.put(
            f"/api/v1/assets/{second['id']}/compatibilities/{gaucho['id']}"
        ).status_code
        == 200
    )
    ambiguous = resolve(client, product, variant, selections=selected)
    assert ambiguous.status_code == 409
    assert "ambigua" in ambiguous.json()["detail"]
    for item in (gaucho, other):
        assert (
            client.patch(
                f"/api/v1/assets/{item['id']}", json={"archived": True}
            ).status_code
            == 200
        )
    missing = resolve(client, product, variant, selections=selected)
    assert missing.status_code == 409
    assert "No hay implementación declarada" in missing.json()["detail"]


def test_database_enforces_source_identity_and_complete_exclusive_pair(
    client: TestClient,
) -> None:
    from app.modules.recipes.models import RecipeStepResource

    _product, _variant, recipe, entry = setup(client)
    item = physical_value(client, entry, 0, "Gaucho")
    saved = save(client, recipe, [final(resources=[dynamic(entry)])])
    other = option(client, "Otra", 1)
    definition_id = UUID(entry["definition_id"])
    value_id = UUID(entry["values"][0]["value_id"])
    with SessionFactory() as session:
        for fields in (
            {},
            {"selection_definition_id": definition_id},
            {"selection_value_id": value_id},
            {
                "selection_definition_id": definition_id,
                "selection_value_id": value_id,
                "asset_revision_id": UUID(item["current_revision_id"]),
            },
            {
                "selection_definition_id": UUID(other["definition_id"]),
                "selection_value_id": value_id,
            },
        ):
            session.add(
                RecipeStepResource(
                    step_id=UUID(saved["steps"][0]["id"]),
                    key="invalid",
                    quantity_per_batch=Decimal("1"),
                    **fields,
                )
            )
            with pytest.raises(IntegrityError):
                session.flush()
            session.rollback()
    assert client.get(f"/api/v1/recipes/{recipe}/plan").json() == saved


def test_multiple_values_keep_distinct_resources_without_quantity_rescaling(
    client: TestClient,
) -> None:
    product, variant, recipe, entry = setup(client)
    hats = option(client, "Sombreros", 2)
    hats["max_selections"] = 2
    first = physical_value(client, hats, 0, "Gaucho")
    second = physical_value(client, hats, 1, "Gaucho ala ancha")
    configure(client, product, [entry, hats])
    first_resource = dynamic(hats)
    second_resource = dynamic(hats, key="wide")
    second_resource["from_selection"]["value_id"] = hats["values"][1]["value_id"]
    save(client, recipe, [final(resources=[first_resource, second_resource])])
    response = resolve(client, product, variant, selections=[selections(hats, 2, "2")])
    assert response.status_code == 200, response.text
    resources = response.json()["plan"]["steps"][0]["resources"]
    assert [value["asset_id"] for value in resources] == [first["id"], second["id"]]
    assert all(Decimal(value["quantity_per_batch"]) == 1 for value in resources)
