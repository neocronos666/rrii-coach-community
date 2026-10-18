from concurrent.futures import ThreadPoolExecutor
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionFactory
from app.modules.production.plan_models import ProductionPlan
from app.modules.recipes.models import Recipe
from tests.integration import test_hito10b_options as catalog_tests
from tests.integration.test_hito9_recipes import setup_recipe
from tests.integration.test_production_api import create_order

pytestmark = pytest.mark.integration
client = catalog_tests.client


def product(client: TestClient) -> tuple[str, str]:
    response = client.post(
        "/api/v1/products",
        json={
            "name": "Figura",
            "initial_variant": {"name": "PLA", "base_unit": "unit"},
        },
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"]), str(response.json()["initial_variant"]["id"])


def base(client: TestClient, product_id: str) -> str:
    response = client.post(
        f"/api/v1/products/{product_id}/recipe", json={"name": "Base"}
    )
    assert response.status_code == 201, response.text
    assert response.json()["product_id"] == product_id
    assert response.json()["product_variant_id"] is None
    return str(response.json()["id"])


def final(**changes: Any) -> dict[str, Any]:
    return {"key": "make", "title": "Fabricar", "is_final_output": True, **changes}


def test_base_recipe_shared_across_variants_without_mutation(
    client: TestClient,
) -> None:
    product_id, pla = product(client)
    petg_response = client.post(
        f"/api/v1/products/{product_id}/variants",
        json={"name": "PETG", "base_unit": "unit"},
    )
    assert petg_response.status_code == 201, petg_response.text
    petg = petg_response.json()["id"]
    recipe = base(client, product_id)
    path = f"/api/v1/recipes/{recipe}/plan"
    saved = client.put(path, json={"steps": [final()]}).json()
    assert saved["steps"][0]["output_variant_id"] is None
    order = create_order(client)
    for variant in (pla, petg):
        preview = client.post(
            f"/api/v1/recipes/{recipe}/production-preview",
            json={"target_quantity": "3", "variant_id": variant},
        )
        assert preview.status_code == 200, preview.text
        response = client.post(
            f"/api/v1/orders/{order}/production-plans",
            json={
                "request_id": str(uuid4()),
                "recipe_id": recipe,
                "variant_id": variant,
                "target_quantity": "3",
            },
        )
        assert response.status_code == 201, response.text
        plan = response.json()
        assert plan["variant_id"] == variant
        assert plan["tasks"][0]["output_variant_id"] == variant
        assert plan["snapshot"]["recipe"]["steps"][0]["output_variant_id"] == variant
        assert plan["snapshot"]["recipe"]["steps"][0]["is_final_output"] is True
        assert client.get(path).json() == saved
    assert client.get(f"/api/v1/products/{product_id}/recipe").json()["id"] == recipe


def test_base_does_not_replace_legacy_alternatives(client: TestClient) -> None:
    legacy, variant = setup_recipe(client)
    read = client.get(f"/api/v1/recipes/{legacy}").json()
    product_id = read["product_id"]
    alternative = client.post(
        f"/api/v1/product-variants/{variant}/recipes", json={"name": "Alternativa"}
    ).json()
    assert client.get(f"/api/v1/products/{product_id}/recipe").status_code == 404
    recipe = base(client, product_id)
    assert client.get(f"/api/v1/recipes/{legacy}").json() == read
    variants = client.get(f"/api/v1/product-variants/{variant}/recipes").json()
    assert {row["id"] for row in variants} == {legacy, alternative["id"]}
    assert (
        client.post(
            f"/api/v1/products/{product_id}/recipe", json={"name": "Otra"}
        ).status_code
        == 409
    )
    assert (
        client.put(
            f"/api/v1/recipes/{recipe}", json={"name": "Base editada", "active": False}
        ).status_code
        == 200
    )
    assert client.get(f"/api/v1/products/{product_id}/recipe").json()["active"] is False
    assert (
        client.post(
            f"/api/v1/products/{product_id}/recipe", json={"name": "Otra"}
        ).status_code
        == 409
    )


def test_concurrent_base_creation_has_one_winner(client: TestClient) -> None:
    product_id, _ = product(client)
    path = f"/api/v1/products/{product_id}/recipe"
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(lambda _: client.post(path, json={"name": "Base"}), range(2))
        )
    assert sorted(response.status_code for response in responses) == [201, 409]
    with SessionFactory() as session:
        assert (
            len(
                session.scalars(
                    select(Recipe).where(Recipe.product_id == UUID(product_id))
                ).all()
            )
            == 1
        )


@pytest.mark.parametrize("case", ["omitted", "foreign", "missing", "inactive", "unit"])
def test_invalid_variant_never_creates_plan(client: TestClient, case: str) -> None:
    product_id, variant = product(client)
    recipe = base(client, product_id)
    assert (
        client.put(
            f"/api/v1/recipes/{recipe}/plan", json={"steps": [final()]}
        ).status_code
        == 200
    )
    extra: dict[str, Any] = {"variant_id": variant}
    expected = 409
    if case == "omitted":
        extra = {}
    elif case == "foreign":
        _, extra["variant_id"] = product(client)
    elif case == "missing":
        extra["variant_id"] = str(uuid4())
        expected = 404
    elif case == "inactive":
        assert (
            client.patch(
                f"/api/v1/product-variants/{variant}", json={"active": False}
            ).status_code
            == 200
        )
    elif case == "unit":
        assert (
            client.put(
                f"/api/v1/recipes/{recipe}/plan", json={"steps": [final(unit="g")]}
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
            **extra,
        },
    )
    assert response.status_code == expected, response.text
    with SessionFactory() as session:
        assert session.scalar(select(ProductionPlan)) is None
    assert client.get("/api/v1/product-allocations").json() == []


@pytest.mark.parametrize(
    "steps",
    [
        [final(), final(key="second")],
        [final(quantity_per_output="2")],
        [final(kind="wait")],
    ],
)
def test_invalid_final_marker_preserves_recipe(
    client: TestClient, steps: list[dict[str, Any]]
) -> None:
    product_id, _ = product(client)
    recipe = base(client, product_id)
    path = f"/api/v1/recipes/{recipe}/plan"
    saved = client.put(path, json={"steps": [final()]}).json()
    assert client.put(path, json={"steps": steps}).status_code in {409, 422}
    assert client.get(path).json() == saved


def test_legacy_cannot_rebind_variant_or_use_final_marker(client: TestClient) -> None:
    recipe, variant = setup_recipe(client)
    path = f"/api/v1/recipes/{recipe}/plan"
    assert client.put(path, json={"steps": [final()]}).status_code == 409
    assert (
        client.put(
            path,
            json={"steps": [final(is_final_output=False, output_variant_id=variant)]},
        ).status_code
        == 200
    )
    _, other = product(client)
    preview = f"/api/v1/recipes/{recipe}/production-preview"
    assert (
        client.post(
            preview, json={"target_quantity": "1", "variant_id": other}
        ).status_code
        == 409
    )
    assert client.post(preview, json={"target_quantity": "1"}).status_code == 200


def test_base_cannot_pin_its_product_output_and_cycles_are_rejected(
    client: TestClient,
) -> None:
    product_id, variant = product(client)
    recipe = base(client, product_id)
    path = f"/api/v1/recipes/{recipe}/plan"
    assert (
        client.put(path, json={"steps": [final(output_variant_id=variant)]}).status_code
        == 409
    )
    assert (
        client.put(
            path,
            json={"steps": [final(is_final_output=False, output_variant_id=variant)]},
        ).status_code
        == 409
    )
    saved = client.put(path, json={"steps": [final()]}).json()
    assert (
        client.put(
            path,
            json={
                "steps": [
                    final(
                        product_inputs=[
                            {"product_variant_id": variant, "quantity_per_batch": "1"}
                        ]
                    )
                ]
            },
        ).status_code
        == 409
    )
    other_recipe, other_variant = setup_recipe(client)
    assert (
        client.put(
            path,
            json={
                "steps": [
                    final(
                        product_inputs=[
                            {
                                "product_variant_id": other_variant,
                                "quantity_per_batch": "1",
                            }
                        ]
                    )
                ]
            },
        ).status_code
        == 200
    )
    assert (
        client.put(
            f"/api/v1/recipes/{other_recipe}/plan",
            json={
                "steps": [
                    final(
                        is_final_output=False,
                        output_variant_id=other_variant,
                        product_inputs=[
                            {"product_variant_id": variant, "quantity_per_batch": "1"}
                        ],
                    )
                ]
            },
        ).status_code
        == 409
    )
    assert saved["steps"][0]["output_variant_id"] is None


def test_selected_variant_is_part_of_idempotency_and_snapshot(
    client: TestClient,
) -> None:
    product_id, variant = product(client)
    recipe = base(client, product_id)
    assert (
        client.put(
            f"/api/v1/recipes/{recipe}/plan", json={"steps": [final()]}
        ).status_code
        == 200
    )
    order = create_order(client)
    path = f"/api/v1/orders/{order}/production-plans"
    payload = {
        "request_id": str(uuid4()),
        "recipe_id": recipe,
        "variant_id": variant,
        "target_quantity": "1",
    }
    response = client.post(path, json=payload)
    assert response.status_code == 201, response.text
    plan = response.json()
    assert client.post(path, json={**payload, "variant_id": None}).status_code == 409
    assert (
        client.put(f"/api/v1/recipes/{recipe}/plan", json={"steps": []}).status_code
        == 200
    )
    assert client.post(path, json=payload).json()["id"] == plan["id"]
    assert (
        client.get(f"/api/v1/production-plans/{plan['id']}").json()["snapshot"]
        == plan["snapshot"]
    )


def test_database_rejects_recipe_variant_of_other_product(client: TestClient) -> None:
    recipe, _ = setup_recipe(client)
    other_product, _ = product(client)
    with SessionFactory() as session:
        row = session.get(Recipe, UUID(recipe))
        assert row is not None
        row.product_id = UUID(other_product)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()
