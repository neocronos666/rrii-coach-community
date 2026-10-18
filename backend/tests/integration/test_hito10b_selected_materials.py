from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.db.exceptions import PersistenceError
from app.db.session import SessionFactory
from app.modules.options.schemas import OptionValueUpdate
from app.modules.options.service import OptionService
from app.modules.production.models import ProductionTask
from app.modules.recipes.models import RecipeSelectedSupplyInput
from tests.integration import test_hito10b_options as catalog
from tests.integration.test_hito9_runs import start
from tests.integration.test_hito10b_base_recipe import final
from tests.integration.test_hito10b_configuration import configure, option, selections
from tests.integration.test_hito10b_recipe_conditions import (
    condition,
    resolve,
    save,
    setup,
)
from tests.integration.test_production_api import create_order

pytestmark = pytest.mark.integration
client = catalog.client


def material(client: TestClient, name: str = "PLA", unit: str = "g") -> str:
    response = client.post(
        "/api/v1/supplies",
        json={"name": name, "category": "material", "base_unit": unit},
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def value_path(entry: dict[str, Any], index: int = 0) -> str:
    value_id = entry["values"][index]["value_id"]
    return f"{catalog.ROOT}/{entry['definition_id']}/values/{value_id}"


def requirement(entry: dict[str, Any], **changes: Any) -> dict[str, Any]:
    return {
        "definition_id": entry["definition_id"],
        "unit": "g",
        "quantity_per_batch": "3",
        **changes,
    }


def bind(
    client: TestClient, entry: dict[str, Any], supply: str, index: int = 0
) -> None:
    response = client.patch(value_path(entry, index), json={"supply_id": supply})
    assert response.status_code == 200, response.text


def test_material_choice_defaults_reservation_history_and_run_consumption(
    client: TestClient,
) -> None:
    product, variant, recipe, accessory = setup(client)
    materials = option(client, "Material", 2)
    pla, petg = material(client), material(client, "PETG")
    bind(client, materials, pla)
    bind(client, materials, petg, 1)
    materials["values"][0]["default_quantity"] = "7"
    accessory["values"][0]["default_quantity"] = "2"
    configure(client, product, [materials, accessory])
    saved = save(
        client,
        recipe,
        [
            {
                "key": "make",
                "title": "Fabricar",
                "when_selected": condition(accessory),
                "scale_by_selection": True,
                "batch_yield": "4",
                "selected_supply_inputs": [requirement(materials)],
            },
            final(key="pack", depends_on=["make"]),
        ],
    )
    response = resolve(client, product, variant, quantity="10")
    assert response.status_code == 200, response.text
    step = response.json()["plan"]["steps"][0]
    assert step["selected_supply_inputs"] == []
    assert step["supply_inputs"][0]["supply_id"] == pla
    assert Decimal(step["supply_inputs"][0]["quantity_per_batch"]) == 3
    assert Decimal(response.json()["planned_steps"][0]["required_quantity"]) == 20
    assert client.get(f"/api/v1/recipes/{recipe}/plan").json() == saved
    chosen = {
        "definition_id": materials["definition_id"],
        "values": [materials["values"][1]],
    }
    petg_plan = resolve(client, product, variant, selections=[chosen])
    assert petg_plan.status_code == 200, petg_plan.text
    assert petg_plan.json()["plan"]["steps"][0]["supply_inputs"][0]["supply_id"] == petg
    order = create_order(client)
    endpoint = f"/api/v1/orders/{order}/production-plans"
    body = {
        "request_id": str(uuid4()),
        "recipe_id": recipe,
        "variant_id": variant,
        "target_quantity": "10",
    }
    created = client.post(endpoint, json=body)
    assert created.status_code == 201, created.text
    task = next(t for t in created.json()["tasks"] if t["recipe_step_key"] == "make")
    reservations = client.get(
        f"/api/v1/production-tasks/{task['id']}/supply-reservations"
    ).json()
    assert len(reservations) == 1
    assert reservations[0]["supply_id"] == pla
    assert Decimal(reservations[0]["quantity"]) == 15
    assert client.get(f"/api/v1/supplies/{pla}/movements").json() == []
    bind(client, materials, petg)
    save(client, recipe, [final()])
    configure(client, product, [])
    retry = client.post(endpoint, json=body)
    assert retry.status_code == 201
    assert retry.json()["snapshot"] == created.json()["snapshot"]
    assert retry.json()["tasks"] == created.json()["tasks"]
    run = start(client, task["id"])
    close = f"/api/v1/production-runs/{run}/close"
    wrong = {
        "good_quantity": "1",
        "supply_consumptions": [{"supply_id": petg, "consumed": "3"}],
    }
    assert client.post(close, json=wrong).status_code == 409
    assert client.get(f"/api/v1/supplies/{petg}/movements").json() == []
    right = {
        "good_quantity": "1",
        "supply_consumptions": [{"supply_id": pla, "consumed": "3"}],
    }
    assert client.post(close, json=right).status_code == 200
    assert client.post(close, json=right).status_code == 200
    assert len(client.get(f"/api/v1/supplies/{pla}/movements").json()) == 1


@pytest.mark.parametrize(
    "failure", ["empty", "multiple", "unbound", "inactive", "unit", "duplicate"]
)
def test_material_errors_are_explicit_without_creating_production(
    client: TestClient, failure: str
) -> None:
    product, variant, recipe, _entry = setup(client)
    entry = option(client, "Material", 2)
    entry["max_selections"] = 2
    supply = material(client, unit="kg" if failure == "unit" else "g")
    if failure != "unbound":
        bind(client, entry, supply)
    bind(client, entry, supply, 1)
    configure(client, product, [entry])
    saved = save(
        client,
        recipe,
        [
            final(
                selected_supply_inputs=[requirement(entry)],
                supply_inputs=[{"supply_id": supply, "quantity_per_batch": "1"}]
                if failure == "duplicate"
                else [],
            )
        ],
    )
    if failure == "inactive":
        assert (
            client.patch(
                f"/api/v1/supplies/{supply}", json={"active": False}
            ).status_code
            == 200
        )
    chosen = [
        selections(
            entry, 0 if failure == "empty" else 2 if failure == "multiple" else 1
        )
    ]
    assert resolve(client, product, variant, selections=chosen).status_code == 409
    preview = client.post(
        f"/api/v1/recipes/{recipe}/production-preview",
        json={"variant_id": variant, "target_quantity": "1", "selections": chosen},
    )
    assert preview.status_code == 409
    order = create_order(client)
    response = client.post(
        f"/api/v1/orders/{order}/production-plans",
        json={
            "request_id": str(uuid4()),
            "recipe_id": recipe,
            "variant_id": variant,
            "target_quantity": "1",
            "selections": chosen,
        },
    )
    assert response.status_code == 409
    with SessionFactory() as session:
        assert (
            list(
                session.scalars(
                    select(ProductionTask).where(ProductionTask.order_id == UUID(order))
                )
            )
            == []
        )
    assert client.get(f"/api/v1/recipes/{recipe}/plan").json() == saved


def test_omitted_step_does_not_require_material(client: TestClient) -> None:
    product, variant, recipe, entry = setup(client)
    save(
        client,
        recipe,
        [
            {
                "key": "make",
                "title": "Fabricar",
                "when_selected": condition(entry),
                "selected_supply_inputs": [requirement(entry)],
            },
            final(key="pack", depends_on=["make"]),
        ],
    )
    response = resolve(client, product, variant)
    assert response.status_code == 200, response.text
    assert response.json()["omitted_step_keys"] == ["make"]
    assert response.json()["plan"]["steps"][0]["depends_on"] == []


def test_material_scope_removed_configuration_and_invalid_inputs(
    client: TestClient,
) -> None:
    product, variant, recipe, entry = setup(client)
    saved = save(client, recipe, [final()])
    for data, status in [
        (requirement(entry, definition_id=str(uuid4())), 409),
        (requirement(entry, quantity_per_batch="0"), 422),
        (requirement(entry, unit="invalid"), 422),
    ]:
        assert (
            client.put(
                f"/api/v1/recipes/{recipe}/plan",
                json={"steps": [final(selected_supply_inputs=[data])]},
            ).status_code
            == status
        )
        assert client.get(f"/api/v1/recipes/{recipe}/plan").json() == saved
    assert (
        client.put(
            f"/api/v1/recipes/{recipe}/plan",
            json={"steps": [final(selected_supply_inputs=[requirement(entry)] * 2)]},
        ).status_code
        == 422
    )
    legacy = client.post(
        f"/api/v1/product-variants/{variant}/recipes", json={"name": "Heredada"}
    ).json()["id"]
    assert (
        client.put(
            f"/api/v1/recipes/{legacy}/plan",
            json={
                "steps": [
                    {
                        "key": "make",
                        "title": "Fabricar",
                        "selected_supply_inputs": [requirement(entry)],
                    }
                ]
            },
        ).status_code
        == 409
    )
    assert (
        client.put(
            f"/api/v1/recipes/{recipe}/plan",
            json={
                "steps": [
                    {
                        "key": "wait",
                        "title": "Esperar",
                        "kind": "wait",
                        "selected_supply_inputs": [requirement(entry)],
                    }
                ]
            },
        ).status_code
        == 422
    )
    save(client, recipe, [final(selected_supply_inputs=[requirement(entry)])])
    configure(client, product, [])
    assert resolve(client, product, variant).status_code == 409
    save(client, recipe, [final()])
    with SessionFactory() as session:
        assert list(session.scalars(select(RecipeSelectedSupplyInput))) == []


def test_material_binding_validation_clear_and_rollback(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = option(client, "Material", 1)
    supply = material(client)
    assert (
        client.patch(value_path(entry), json={"supply_id": str(uuid4())}).status_code
        == 404
    )
    bind(client, entry, supply)
    before = client.get(value_path(entry)).json()
    with SessionFactory() as session:

        def fail() -> None:
            session.flush()
            raise SQLAlchemyError("Fallo simulado")

        monkeypatch.setattr(session, "commit", fail)
        with pytest.raises(PersistenceError):
            OptionService(session).update_value(
                UUID(entry["definition_id"]),
                UUID(entry["values"][0]["value_id"]),
                OptionValueUpdate(supply_id=None),
            )
    assert client.get(value_path(entry)).json() == before
    assert (
        client.patch(value_path(entry), json={"supply_id": None}).json()["supply_id"]
        is None
    )
    assert (
        client.patch(f"/api/v1/supplies/{supply}", json={"active": False}).status_code
        == 200
    )
    assert (
        client.patch(value_path(entry), json={"supply_id": supply}).status_code == 409
    )


def test_material_resolution_keeps_one_snapshot_during_binding_change(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.modules.recipes.resolution import (
        RecipeResolutionService,
        RecipeResolveInput,
    )
    from app.modules.recipes.schemas import PlanRead

    product, variant, recipe, entry = setup(client)
    pla, petg = material(client), material(client, "PETG")
    bind(client, entry, pla)
    entry["values"][0]["default_quantity"] = "1"
    configure(client, product, [entry])
    save(client, recipe, [final(selected_supply_inputs=[requirement(entry)])])
    with SessionFactory() as session:
        service = RecipeResolutionService(session)
        original = service.recipes.plan

        def concurrent_change(recipe_id: UUID) -> PlanRead:
            bind(client, entry, petg)
            return original(recipe_id)

        monkeypatch.setattr(service.recipes, "plan", concurrent_change)
        result = service.resolve(
            UUID(product),
            RecipeResolveInput(variant_id=UUID(variant), quantity=Decimal("1")),
        )
        assert str(result.plan.steps[0].supply_inputs[0].supply_id) == pla
        assert str(result.configuration.selections[0].values[0].supply_id) == pla
    current = resolve(client, product, variant)
    assert current.status_code == 200, current.text
    assert current.json()["plan"]["steps"][0]["supply_inputs"][0]["supply_id"] == petg


def test_combined_material_limit_is_checked_before_persistence(
    client: TestClient,
) -> None:
    _product, _variant, recipe, entry = setup(client)
    saved = save(client, recipe, [final()])
    response = client.put(
        f"/api/v1/recipes/{recipe}/plan",
        json={
            "steps": [
                final(
                    supply_inputs=[
                        {"supply_id": str(uuid4()), "quantity_per_batch": "1"}
                        for _ in range(100)
                    ],
                    selected_supply_inputs=[requirement(entry)],
                )
            ]
        },
    )
    assert response.status_code == 422, response.text
    assert "100 insumos" in response.text
    assert client.get(f"/api/v1/recipes/{recipe}/plan").json() == saved
