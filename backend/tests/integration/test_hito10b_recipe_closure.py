from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionFactory
from app.modules.production.models import (
    ProductionTaskAssetRevision,
    ProductionTaskDependency,
)
from tests.integration import test_hito10b_options as catalog
from tests.integration.test_hito10b_base_recipe import base, final, product
from tests.integration.test_hito10b_configuration import (
    configure,
    option,
    physical_value,
)
from tests.integration.test_hito10b_machine_assignment import machine
from tests.integration.test_hito10b_recipe_conditions import condition, resolve, save
from tests.integration.test_hito10b_recipe_steps import service, service_step
from tests.integration.test_hito10b_selected_materials import (
    bind,
    material,
    requirement,
)
from tests.integration.test_hito10b_selection_resources import dynamic
from tests.integration.test_production_api import create_order, create_project

pytestmark = pytest.mark.integration
client = catalog.client


@pytest.mark.parametrize("scope", ["order", "component"])
@pytest.mark.parametrize("automatic", [False, True])
def test_combined_recipe_resolution_and_historical_production(
    client: TestClient, scope: str, automatic: bool
) -> None:
    product_id, variant = product(client)
    recipe = base(client, product_id)
    hats = option(client, "Sombrero", 1)
    materials = option(client, "Material", 1)
    coating = option(client, "Acabado", 1)
    gaucho = physical_value(client, hats, 0, "Gaucho")
    pla = material(client)
    bind(client, materials, pla)
    hats["values"][0]["default_quantity"] = "2"
    materials["values"][0]["default_quantity"] = "9"
    configure(client, product_id, [hats, materials, coating])
    sanding = service(client)
    printer = machine(client, "Impresora")
    saved = save(
        client,
        recipe,
        [
            {
                "key": "print",
                "title": "Imprimir",
                "task_type": "fdm_print",
                "required_machine_type": "fdm_printer",
                "batch_yield": "4",
                "when_selected": condition(hats),
                "scale_by_selection": True,
                "resources": [dynamic(hats)],
                "selected_supply_inputs": [requirement(materials)],
            },
            {
                "key": "coat",
                "title": "Aplicar acabado",
                "when_selected": condition(coating),
                "depends_on": ["print"],
            },
            service_step(
                sanding,
                when_selected=condition(hats),
                scale_by_selection=True,
                action_context={} if automatic else {"piece": "sombrero Gaucho"},
                action_template="Lijar {quantity} de {piece} para {product} ({design})"
                if automatic
                else None,
                resources=[dynamic(hats)],
                depends_on=["coat"],
            ),
            final(key="pack", depends_on=["sand"]),
        ],
    )
    resolution = resolve(client, product_id, variant, quantity="10")
    assert resolution.status_code == 200, resolution.text
    resolved = resolution.json()
    assert resolved["omitted_step_keys"] == ["coat"]
    planned = {step["key"]: step for step in resolved["planned_steps"]}
    assert Decimal(planned["print"]["required_quantity"]) == 20
    assert Decimal(planned["print"]["batches"]) == 5
    assert Decimal(planned["sand"]["required_quantity"]) == 20
    assert Decimal(planned["pack"]["required_quantity"]) == 10
    preview = client.post(
        f"/api/v1/recipes/{recipe}/production-preview",
        json={"variant_id": variant, "target_quantity": "10"},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["configuration"] == resolved["configuration"]
    assert preview.json()["steps"] == resolved["planned_steps"]
    if scope == "order":
        destination = create_order(client)
        endpoint = f"/api/v1/orders/{destination}/production-plans"
    else:
        _project, destination = create_project(client)
        endpoint = f"/api/v1/project-components/{destination}/production-plans"
    payload = {
        "request_id": str(uuid4()),
        "recipe_id": recipe,
        "variant_id": variant,
        "target_quantity": "10",
        "machine_assignments": {"print": printer},
    }
    created = client.post(endpoint, json=payload)
    assert created.status_code == 201, created.text
    record = created.json()
    assert record["snapshot"]["configuration"] == resolved["configuration"]
    assert record["snapshot"]["planning"] == resolved["planned_steps"]
    tasks = {task["recipe_step_key"]: task for task in record["tasks"]}
    assert set(tasks) == {"print", "sand", "pack"}
    for task in tasks.values():
        assert task["order_id"] == (destination if scope == "order" else None)
        assert task["project_component_id"] == (
            destination if scope == "component" else None
        )
    assert tasks["print"]["machine_id"] == printer
    assert tasks["sand"]["machine_id"] is None
    sand_snapshot = tasks["sand"]["recipe_snapshot"]["step"]
    assert sand_snapshot["service_action"] == (
        "Lijar 20 de Gaucho para Figura (Gaucho)"
        if automatic
        else "Lijar sombrero Gaucho"
    )
    resolved_sand = next(
        step for step in resolved["plan"]["steps"] if step["key"] == "sand"
    )
    assert sand_snapshot == {
        key: value
        for key, value in resolved_sand.items()
        if key not in {"id", "position"}
    }
    assert sand_snapshot["depends_on"] == ["print"]
    for key in ("print", "sand"):
        step = tasks[key]["recipe_snapshot"]["step"]
        assert (
            step["resources"][0]["asset_revision_id"] == gaucho["current_revision_id"]
        )
        assert step["selected_supply_inputs"] == []
    reservations = client.get(
        f"/api/v1/production-tasks/{tasks['print']['id']}/supply-reservations"
    ).json()
    assert len(reservations) == 1 and reservations[0]["supply_id"] == pla
    assert Decimal(reservations[0]["quantity"]) == 15
    assert client.get(f"/api/v1/supplies/{pla}/movements").json() == []
    with SessionFactory() as session:
        for key in ("print", "sand"):
            refs = list(
                session.scalars(
                    select(ProductionTaskAssetRevision.asset_revision_id).where(
                        ProductionTaskAssetRevision.task_id == UUID(tasks[key]["id"])
                    )
                )
            )
            assert refs == [UUID(gaucho["current_revision_id"])]
        edges = set(
            session.execute(
                select(
                    ProductionTaskDependency.task_id,
                    ProductionTaskDependency.depends_on_task_id,
                )
            ).tuples()
        )
        assert edges == {
            (UUID(tasks["sand"]["id"]), UUID(tasks["print"]["id"])),
            (UUID(tasks["pack"]["id"]), UUID(tasks["sand"]["id"])),
        }
    assert client.get(f"/api/v1/recipes/{recipe}/plan").json() == saved
    assert (
        client.post(f"/api/v1/assets/{gaucho['id']}/revisions", json={}).status_code
        == 201
    )
    bind(client, materials, material(client, "PETG"))
    assert (
        client.patch(
            f"/api/v1/assets/{gaucho['id']}", json={"name": "Diseño nuevo"}
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/v1/products/{product_id}", json={"name": "Producto nuevo"}
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/v1/service-definitions/{sanding}",
            json={"action_template": "Pulir {piece}"},
        ).status_code
        == 200
    )
    save(client, recipe, [final()])
    configure(client, product_id, [])
    retry = client.post(endpoint, json=payload)
    assert retry.status_code == 201, retry.text
    assert retry.json()["id"] == record["id"]
    assert retry.json()["snapshot"] == record["snapshot"]
    assert retry.json()["tasks"] == record["tasks"]
