from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionFactory
from app.modules.assets.file_models import StoredFile
from app.modules.assets.models import AssetRevision
from app.modules.assets.storage import LocalAssetStorage
from app.modules.production.models import ProductionTaskAssetRevision
from app.modules.recipes.models import RecipeStepResource
from tests.integration import test_hito10b_asset_files as file_tests
from tests.integration import test_hito10b_asset_structure as structure_tests
from tests.integration import test_hito10b_options as catalog_tests
from tests.integration.test_hito9_recipes import setup_recipe
from tests.integration.test_hito10b_base_recipe import base, final, product
from tests.integration.test_production_api import create_order

pytestmark = pytest.mark.integration
client = catalog_tests.client
storage = file_tests.storage


def asset(client: TestClient, name: str = "Brazo") -> dict[str, Any]:
    response = client.post("/api/v1/assets", json={"name": name})
    assert response.status_code == 201, response.text
    return dict(response.json())


def resource(revision: str, key: str = "arm", **changes: Any) -> dict[str, Any]:
    return {"key": key, "asset_revision_id": revision, **changes}


def test_resources_without_stl_quantities_and_reuse_per_step(
    client: TestClient,
) -> None:
    item = asset(client)
    recipe, variant = setup_recipe(client)
    service = client.post(
        "/api/v1/service-definitions", json={"name": "Lijado"}
    ).json()["id"]
    path = f"/api/v1/recipes/{recipe}/plan"
    resources = [
        resource(
            item["current_revision_id"],
            "left",
            quantity_per_batch="2",
            label="Izquierdo",
        ),
        resource(item["current_revision_id"], "right", quantity_per_batch="0.25"),
    ]
    response = client.put(
        path,
        json={
            "steps": [
                {
                    "key": "make",
                    "title": "Imprimir",
                    "task_type": "fdm_print",
                    "resources": resources,
                    "output_variant_id": variant,
                },
                {
                    "key": "sand",
                    "title": "Lijar",
                    "kind": "service",
                    "service_definition_id": service,
                    "resources": [resources[0]],
                    "depends_on": ["make"],
                },
                {
                    "key": "wait",
                    "title": "Dejar secar",
                    "kind": "wait",
                    "resources": [resources[0]],
                    "depends_on": ["sand"],
                },
            ]
        },
    )
    assert response.status_code == 200, response.text
    saved = response.json()
    assert client.get(path).json() == saved
    left, right = saved["steps"][0]["resources"]
    assert left["asset_id"] == item["id"]
    assert left["code"] == item["code"]
    assert left["name"] == "Brazo"
    assert left["revision_number"] == 1
    assert left["label"] == "Izquierdo"
    assert Decimal(left["quantity_per_batch"]) == 2
    assert Decimal(right["quantity_per_batch"]) == Decimal("0.25")
    assert "files" not in left and "components" not in left
    with SessionFactory() as session:
        assert session.scalar(select(func.count()).select_from(StoredFile)) == 0
        assert session.scalar(select(func.count()).select_from(RecipeStepResource)) == 4


@pytest.mark.parametrize(
    "changes",
    [
        {"quantity_per_batch": "0"},
        {"quantity_per_batch": "-1"},
        {"quantity_per_batch": "0.0000001"},
        {"quantity_per_batch": "NaN"},
        {"asset_id": str(uuid4())},
        {"key": "invalid key"},
        {"label": ""},
    ],
)
def test_invalid_resource_payload_preserves_plan(
    client: TestClient, changes: dict[str, Any]
) -> None:
    item = asset(client)
    recipe, variant = setup_recipe(client)
    path = f"/api/v1/recipes/{recipe}/plan"
    step = {
        "key": "make",
        "title": "Fabricar",
        "output_variant_id": variant,
        "resources": [resource(item["current_revision_id"])],
    }
    saved = client.put(path, json={"steps": [step]}).json()
    invalid = {**step, "resources": [resource(item["current_revision_id"], **changes)]}
    assert client.put(path, json={"steps": [invalid]}).status_code == 422
    assert client.get(path).json() == saved


def test_missing_revision_and_duplicate_key_are_atomic(client: TestClient) -> None:
    item = asset(client)
    recipe, variant = setup_recipe(client)
    path = f"/api/v1/recipes/{recipe}/plan"
    step = {
        "key": "make",
        "title": "Fabricar",
        "output_variant_id": variant,
        "resources": [resource(item["current_revision_id"])],
    }
    saved = client.put(path, json={"steps": [step]}).json()
    assert (
        client.put(
            path, json={"steps": [{**step, "resources": [resource(str(uuid4()))]}]}
        ).status_code
        == 409
    )
    assert (
        client.put(
            path,
            json={
                "steps": [
                    {**step, "resources": [resource(item["current_revision_id"])] * 2}
                ]
            },
        ).status_code
        == 422
    )
    assert client.get(path).json() == saved


def test_base_recipe_resource_stl_is_not_copied(
    client: TestClient, storage: LocalAssetStorage
) -> None:
    item = asset(client)
    file_tests.upload(
        client, f"/api/v1/assets/{item['id']}/revisions/{item['current_revision_id']}"
    )
    product_id, variant = product(client)
    recipe = base(client, product_id)
    use = resource(item["current_revision_id"])
    assert (
        client.put(
            f"/api/v1/recipes/{recipe}/plan",
            json={"steps": [final(resources=[use, {**use, "key": "other"}])]},
        ).status_code
        == 200
    )
    order = create_order(client)
    response = client.post(
        f"/api/v1/orders/{order}/production-plans",
        json={
            "request_id": str(uuid4()),
            "recipe_id": recipe,
            "variant_id": variant,
            "target_quantity": "2",
        },
    )
    assert response.status_code == 201, response.text
    task = response.json()["tasks"][0]
    assert len(task["recipe_snapshot"]["step"]["resources"]) == 2
    with SessionFactory() as session:
        assert session.scalar(select(func.count()).select_from(StoredFile)) == 1
        refs = session.scalars(
            select(ProductionTaskAssetRevision).where(
                ProductionTaskAssetRevision.task_id == UUID(task["id"])
            )
        ).all()
        assert len(refs) == 1
        assert str(refs[0].asset_revision_id) == item["current_revision_id"]
    assert storage.root.exists()


def test_history_keeps_revision_and_metadata_after_recipe_replacement(
    client: TestClient,
) -> None:
    item = asset(client)
    pinned = item["current_revision_id"]
    recipe, variant = setup_recipe(client)
    path = f"/api/v1/recipes/{recipe}/plan"
    assert (
        client.put(
            path,
            json={
                "steps": [
                    {
                        "key": "make",
                        "title": "Fabricar",
                        "output_variant_id": variant,
                        "batch_yield": "3",
                        "resources": [resource(pinned, quantity_per_batch="2")],
                    }
                ]
            },
        ).status_code
        == 200
    )
    order = create_order(client)
    endpoint = f"/api/v1/orders/{order}/production-plans"
    payload = {"request_id": str(uuid4()), "recipe_id": recipe, "target_quantity": "10"}
    response = client.post(endpoint, json=payload)
    assert response.status_code == 201, response.text
    plan = response.json()
    assert Decimal(plan["snapshot"]["planning"][0]["batches"]) == 4
    revision = client.post(f"/api/v1/assets/{item['id']}/revisions", json={})
    assert revision.status_code == 201
    assert (
        client.patch(
            f"/api/v1/assets/{item['id']}",
            json={"name": "Brazo corregido", "archived": True},
        ).status_code
        == 200
    )
    current = client.get(path).json()["steps"][0]["resources"][0]
    assert current["asset_revision_id"] == pinned
    assert current["revision_number"] == 1 and current["archived"] is True
    assert (
        client.post(endpoint, json={**payload, "request_id": str(uuid4())}).status_code
        == 201
    )
    assert client.put(path, json={"steps": []}).status_code == 200
    historical = client.get(f"/api/v1/production-plans/{plan['id']}").json()
    assert historical["snapshot"] == plan["snapshot"]
    assert historical["tasks"] == plan["tasks"]
    assert client.post(endpoint, json=payload).json()["id"] == plan["id"]
    with SessionFactory() as session:
        assert session.scalar(select(func.count()).select_from(RecipeStepResource)) == 0
        with pytest.raises(IntegrityError) as error:
            session.execute(
                delete(AssetRevision).where(AssetRevision.id == UUID(pinned))
            )
        assert "production_task_asset_revisions" in str(error.value.orig)
        session.rollback()


def test_nested_composition_stays_pinned_until_recipe_adopts_revision(
    client: TestClient,
) -> None:
    leaf = asset(client, "Palo")
    middle = structure_tests.publish(
        client, asset(client, "Par"), [structure_tests.component(leaf, "2")]
    )
    root = structure_tests.publish(
        client, asset(client, "Juego"), [structure_tests.component(middle, "5")]
    )
    recipe, variant = setup_recipe(client)
    path = f"/api/v1/recipes/{recipe}/plan"
    step = {
        "key": "make",
        "title": "Fabricar juego",
        "output_variant_id": variant,
        "resources": [
            resource(str(root["current_revision_id"]), "set", quantity_per_batch="3")
        ],
    }
    assert client.put(path, json={"steps": [step]}).status_code == 200
    assert (
        client.post(f"/api/v1/assets/{leaf['id']}/revisions", json={}).status_code
        == 201
    )
    old_children = structure_tests.composition(client, middle)
    assert old_children[0]["child_revision_id"] == leaf["current_revision_id"]
    assert Decimal(str(old_children[0]["quantity"])) == 2
    assert Decimal(str(structure_tests.composition(client, root)[0]["quantity"])) == 5
    old_revision = root["current_revision_id"]
    new_leaf = client.get(f"/api/v1/assets/{leaf['id']}").json()
    new_middle = structure_tests.publish(
        client, middle, [structure_tests.component(new_leaf, "4")]
    )
    new_root = structure_tests.publish(
        client, root, [structure_tests.component(new_middle, "7")]
    )
    newer = str(new_root["current_revision_id"])
    assert (
        structure_tests.composition(client, root)[0]["child_revision_id"]
        == middle["current_revision_id"]
    )
    assert (
        structure_tests.composition(client, new_middle)[0]["child_revision_id"]
        == new_leaf["current_revision_id"]
    )
    assert (
        Decimal(str(structure_tests.composition(client, new_root)[0]["quantity"])) == 7
    )
    assert (
        Decimal(str(structure_tests.composition(client, new_middle)[0]["quantity"]))
        == 4
    )
    assert (
        client.get(path).json()["steps"][0]["resources"][0]["asset_revision_id"]
        == old_revision
    )
    updated = {**step, "resources": [resource(newer, "set", quantity_per_batch="3")]}
    assert (
        client.put(path, json={"steps": [updated]}).json()["steps"][0]["resources"][0][
            "asset_revision_id"
        ]
        == newer
    )
