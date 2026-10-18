from collections.abc import Iterator
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import SessionFactory
from app.main import app
from app.modules.products.models import Product, ProductVariant
from app.modules.recipes.models import (
    Recipe,
    RecipeProductInput,
    RecipeStep,
    RecipeStepDependency,
    RecipeSupplyInput,
)
from app.modules.supplies.models import Supply

pytestmark = pytest.mark.integration


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client
    with SessionFactory() as session:
        for model in (
            RecipeSupplyInput,
            RecipeProductInput,
            RecipeStepDependency,
            RecipeStep,
            Recipe,
            ProductVariant,
            Product,
            Supply,
        ):
            session.execute(delete(model))
        session.commit()


def setup_recipe(client: TestClient) -> tuple[str, str]:
    product = client.post(
        "/api/v1/products",
        json={
            "name": "Figura",
            "initial_variant": {"name": "PLA", "base_unit": "unit"},
        },
    )
    assert product.status_code == 201
    variant = str(product.json()["initial_variant"]["id"])
    recipe = client.post(
        f"/api/v1/product-variants/{variant}/recipes", json={"name": "FDM"}
    )
    assert recipe.status_code == 201
    return str(recipe.json()["id"]), variant


def step(key: str, dependencies: list[str] | None = None) -> dict[str, object]:
    return {
        "key": key,
        "title": key,
        "task_type": "manual",
        "unit": "unit",
        "quantity_per_output": "1",
        "batch_yield": "12",
        "depends_on": dependencies or [],
    }


def test_alternative_recipes_and_mutable_dag(client: TestClient) -> None:
    recipe, variant = setup_recipe(client)
    assert (
        client.post(
            f"/api/v1/product-variants/{variant}/recipes", json={"name": "Alternativa"}
        ).status_code
        == 201
    )
    assert len(client.get(f"/api/v1/product-variants/{variant}/recipes").json()) == 2
    plan = {
        "steps": [
            step("print"),
            {**step("assemble", ["print"]), "output_variant_id": variant},
        ]
    }
    response = client.put(f"/api/v1/recipes/{recipe}/plan", json=plan)
    assert response.status_code == 200, response.text
    assert response.json()["steps"][1]["depends_on"] == ["print"]
    assert client.get(f"/api/v1/recipes/{recipe}/plan").json() == response.json()
    revised = client.put(
        f"/api/v1/recipes/{recipe}/plan", json={"steps": [step("manual")]}
    )
    assert revised.status_code == 200
    assert [s["key"] for s in revised.json()["steps"]] == ["manual"]


@pytest.mark.parametrize(
    "steps",
    [
        [step("a", ["a"])],
        [step("a", ["b"]), step("b", ["a"])],
        [step("a", ["missing"])],
        [step("a"), step("a")],
        [step("a"), step("b", ["a", "a"])],
    ],
)
def test_dag_rejection_preserves_plan(
    client: TestClient, steps: list[dict[str, object]]
) -> None:
    recipe, _ = setup_recipe(client)
    path = f"/api/v1/recipes/{recipe}/plan"
    original = client.put(path, json={"steps": [step("original")]}).json()
    assert client.put(path, json={"steps": steps}).status_code == 422
    assert client.get(path).json() == original


def test_invalid_output_unit_and_machine_preserve_plan(client: TestClient) -> None:
    recipe, variant = setup_recipe(client)
    path = f"/api/v1/recipes/{recipe}/plan"
    original = client.put(path, json={"steps": [step("original")]}).json()
    invalid = {**step("wrong"), "output_variant_id": variant, "unit": "g"}
    assert client.put(path, json={"steps": [invalid]}).status_code == 409
    # La máquina física ya no forma parte del contrato de Recipe (10B.4c).
    invalid = {**step("wrong"), "suggested_machine_id": str(uuid4())}
    assert client.put(path, json={"steps": [invalid]}).status_code == 422
    assert client.get(path).json() == original


def test_inputs_multiplicity_and_physical_cycles(client: TestClient) -> None:
    recipe, final = setup_recipe(client)
    component_recipe, component = setup_recipe(client)
    supply = client.post(
        "/api/v1/supplies",
        json={"name": "Pegamento", "category": "consumable", "base_unit": "ml"},
    )
    assert supply.status_code == 201
    path = f"/api/v1/recipes/{recipe}/plan"
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
                "supply_inputs": [
                    {"supply_id": supply.json()["id"], "quantity_per_batch": "3"}
                ],
            },
        ]
    }
    saved = client.put(path, json=body)
    assert saved.status_code == 200, saved.text
    inputs = saved.json()["steps"][1]
    assert Decimal(inputs["product_inputs"][0]["quantity_per_batch"]) == Decimal("48")
    assert inputs["product_inputs"][0]["source_step_key"] == "print"
    assert Decimal(inputs["supply_inputs"][0]["quantity_per_batch"]) == Decimal("3")
    cycle = {
        "steps": [
            {
                **step("cycle"),
                "output_variant_id": component,
                "product_inputs": [
                    {"product_variant_id": final, "quantity_per_batch": "1"}
                ],
            }
        ]
    }
    assert (
        client.put(f"/api/v1/recipes/{component_recipe}/plan", json=cycle).status_code
        == 409
    )
    assert client.get(path).json() == saved.json()
    assert client.put(path, json={"steps": [step("replacement")]}).status_code == 200


def test_input_reference_and_duplicate_validation(client: TestClient) -> None:
    recipe, final = setup_recipe(client)
    _, component = setup_recipe(client)
    path = f"/api/v1/recipes/{recipe}/plan"
    reference = {
        "product_variant_id": component,
        "quantity_per_batch": "1",
        "source_step_key": "missing",
    }
    assert (
        client.put(
            path, json={"steps": [{**step("a"), "product_inputs": [reference]}]}
        ).status_code
        == 422
    )
    duplicate = {"product_variant_id": component, "quantity_per_batch": "1"}
    assert (
        client.put(
            path,
            json={"steps": [{**step("a"), "product_inputs": [duplicate, duplicate]}]},
        ).status_code
        == 422
    )
    self_input = {"product_variant_id": final, "quantity_per_batch": "1"}
    assert (
        client.put(
            path, json={"steps": [{**step("a"), "product_inputs": [self_input]}]}
        ).status_code
        == 409
    )
