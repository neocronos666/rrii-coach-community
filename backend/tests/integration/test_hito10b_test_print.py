from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db.exceptions import PersistenceError
from app.db.session import SessionFactory
from app.modules.assets.models import AssetRevision
from app.modules.production.models import ProductionTask
from app.modules.production.run_models import ProductionRun
from app.modules.production.run_schemas import RunClose
from app.modules.production.test_print_service import TestPrintService as PrintService
from app.modules.products.stock_models import ProductStockMovement
from tests.integration import test_hito10b_options as catalog
from tests.integration.test_hito9_runs import new_task
from tests.integration.test_hito9_runs import start as start_normal
from tests.integration.test_hito10b_base_recipe import base, final, product
from tests.integration.test_hito10b_configuration import (
    configure,
    option,
    physical_value,
)
from tests.integration.test_hito10b_machine_assignment import machine
from tests.integration.test_hito10b_recipe_conditions import condition, save
from tests.integration.test_hito10b_recipe_steps import service, service_step
from tests.integration.test_hito10b_selected_materials import (
    bind,
    material,
    requirement,
)
from tests.integration.test_hito10b_selection_resources import dynamic
from tests.integration.test_production_api import mark_legacy

pytestmark = pytest.mark.integration
client = catalog.client
ROOT = "/api/v1/test-prints"


def setup(client: TestClient) -> dict[str, Any]:
    product_id, variant = product(client)
    _, component = product(client)
    recipe = base(client, product_id)
    hats = option(client, "Sombrero", 1)
    materials = option(client, "Material", 1)
    optional = option(client, "Pintura", 1)
    asset = physical_value(client, hats, 0, "Gaucho")
    supply = material(client)
    bind(client, materials, supply)
    hats["values"][0]["default_quantity"] = "1"
    materials["values"][0]["default_quantity"] = "1"
    configure(client, product_id, [hats, materials, optional])
    printer = machine(client, "Impresora")
    sanding = service(client)
    save(
        client,
        recipe,
        [
            {
                "key": "print",
                "title": "Imprimir",
                "task_type": "fdm_print",
                "output_variant_id": component,
                "batch_yield": "4",
                "resources": [dynamic(hats)],
                "selected_supply_inputs": [requirement(materials)],
            },
            {
                "key": "paint",
                "title": "Pintar",
                "when_selected": condition(optional),
                "depends_on": ["print"],
            },
            service_step(
                sanding,
                action_context={},
                resources=[dynamic(hats)],
                depends_on=["paint"],
            ),
            {"key": "wait", "title": "Secar", "kind": "wait", "depends_on": ["sand"]},
            final(
                key="pack",
                depends_on=["print", "wait"],
                product_inputs=[
                    {
                        "product_variant_id": component,
                        "quantity_per_batch": "1",
                        "source_step_key": "print",
                    }
                ],
            ),
        ],
    )
    payload = {
        "request_id": str(uuid4()),
        "recipe_id": recipe,
        "variant_id": variant,
        "target_quantity": "2",
        "machine_assignments": {"print": printer},
    }
    response = client.post(ROOT, json=payload)
    assert response.status_code == 201, response.text
    return {
        "record": response.json(),
        "payload": payload,
        "supply": supply,
        "component": component,
        "product": product_id,
        "asset": asset,
        "printer": printer,
        "materials": materials,
    }


def start(client: TestClient, case: dict[str, Any], key: str, **changes: Any) -> str:
    response = client.post(
        f"{ROOT}/{case['record']['id']}/steps/{key}/runs",
        json={"request_id": str(uuid4()), **changes},
    )
    assert response.status_code == 201, response.text
    assert response.json()["task_id"] is None
    assert response.json()["test_print_step_id"] is not None
    return str(response.json()["id"])


def close(client: TestClient, run: str, **changes: Any) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/production-runs/{run}/close", json={"good_quantity": "2", **changes}
    )
    assert response.status_code == 200, response.text
    return dict(response.json())


def consume(case: dict[str, Any]) -> list[dict[str, str]]:
    return [{"supply_id": case["supply"], "consumed": "3", "wasted": "1"}]


def finish(client: TestClient, case: dict[str, Any]) -> None:
    close(
        client,
        start(client, case, "print"),
        good_quantity="4",
        supply_consumptions=consume(case),
    )
    for key in ("sand", "wait"):
        close(client, start(client, case, key))
    close(
        client,
        start(client, case, "pack"),
        product_consumptions=[
            {
                "variant_id": case["component"],
                "consumed": "2",
            }
        ],
    )


def stock(client: TestClient, variant: str) -> Decimal:
    return Decimal(
        client.get(f"/api/v1/product-variants/{variant}/stock").json()[
            "physical_quantity"
        ]
    )


def test_complete_dag_consumes_once_and_promotes_only_final_output(
    client: TestClient,
) -> None:
    case = setup(client)
    record = case["record"]
    assert record["snapshot"]["omitted_step_keys"] == ["paint"]
    steps = {step["key"]: step for step in record["steps"]}
    assert steps["sand"]["snapshot"]["depends_on"] == ["print"]
    assert steps["sand"]["snapshot"]["service_action"] == "Lijar Gaucho"
    with SessionFactory() as session:
        assert session.scalar(select(func.count()).select_from(ProductionTask)) == 0
    assert (
        client.post(
            f"{ROOT}/{record['id']}/steps/pack/runs", json={"request_id": str(uuid4())}
        ).status_code
        == 409
    )
    promotion = {"request_id": str(uuid4()), "quantity": "2"}
    assert (
        client.post(f"{ROOT}/{record['id']}/promote", json=promotion).status_code == 409
    )
    run = start(client, case, "print")
    result = close(client, run, good_quantity="4", supply_consumptions=consume(case))
    repeated = close(client, run, good_quantity="4", supply_consumptions=consume(case))
    assert result == repeated
    assert len(client.get(f"/api/v1/supplies/{case['supply']}/movements").json()) == 1
    assert stock(client, case["component"]) == 0
    assert stock(client, case["payload"]["variant_id"]) == 0
    for key in ("sand", "wait"):
        close(client, start(client, case, key))
        assert (
            client.post(f"{ROOT}/{record['id']}/promote", json=promotion).status_code
            == 409
        )
    final_run = start(client, case, "pack")
    closed = close(
        client,
        final_run,
        product_consumptions=[{"variant_id": case["component"], "consumed": "2"}],
    )
    assert closed["warnings"] == []
    usages = client.get(
        f"/api/v1/production-runs/{final_run}/product-consumptions"
    ).json()
    assert usages[0]["internal_source_step_id"] == steps["print"]["id"]
    assert (
        stock(client, case["component"])
        == stock(client, case["payload"]["variant_id"])
        == 0
    )
    assert client.get(f"{ROOT}/{record['id']}").json()["status"] == "completed"
    promoted = client.post(f"{ROOT}/{record['id']}/promote", json=promotion)
    assert promoted.status_code == 201, promoted.text
    assert promoted.json()["test_print_id"] == record["id"]
    assert promoted.json()["movement_type"] == "test_print"
    assert (
        client.post(f"{ROOT}/{record['id']}/promote", json=promotion).json()
        == promoted.json()
    )
    assert stock(client, case["payload"]["variant_id"]) == 2
    assert len(client.get(f"/api/v1/supplies/{case['supply']}/movements").json()) == 1
    assert (
        client.post(
            f"{ROOT}/{record['id']}/promote", json={**promotion, "quantity": "1"}
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"{ROOT}/{record['id']}/promote",
            json={**promotion, "variant_id": case["component"]},
        ).status_code
        == 422
    )


def test_history_survives_recipe_options_assets_and_material_changes(
    client: TestClient,
) -> None:
    case = setup(client)
    initial = case["record"]
    save(client, case["payload"]["recipe_id"], [final()])
    configure(client, case["product"], [])
    client.post(f"/api/v1/assets/{case['asset']['id']}/revisions", json={})
    bind(client, case["materials"], material(client, "PETG"))
    assert client.post(ROOT, json=case["payload"]).json() == initial
    finish(client, case)
    assert (
        client.get(f"{ROOT}/{initial['id']}").json()["snapshot"] == initial["snapshot"]
    )
    with SessionFactory() as session:
        with pytest.raises(IntegrityError):
            session.execute(
                delete(AssetRevision).where(
                    AssetRevision.id == UUID(case["asset"]["current_revision_id"])
                )
            )
        session.rollback()
    promotion = {"request_id": str(uuid4()), "quantity": "1"}
    first = client.post(f"{ROOT}/{initial['id']}/promote", json=promotion)
    assert first.status_code == 201
    client.patch(
        f"/api/v1/product-variants/{case['payload']['variant_id']}",
        json={"active": False},
    )
    assert (
        client.post(f"{ROOT}/{initial['id']}/promote", json=promotion).json()
        == first.json()
    )


def test_failures_retries_internal_shortage_and_rollback(client: TestClient) -> None:
    case = setup(client)
    run = start(client, case, "print")
    assert (
        client.post(
            f"/api/v1/production-runs/{run}/close", json={"good_quantity": "2"}
        ).status_code
        == 409
    )
    assert client.get(f"/api/v1/production-runs/{run}").json()["status"] == "running"
    close(
        client,
        run,
        good_quantity="0",
        failed_quantity="2",
        failure_reason="adhesion",
        supply_consumptions=consume(case),
    )
    assert (
        client.post(
            f"{ROOT}/{case['record']['id']}/steps/sand/runs",
            json={"request_id": str(uuid4())},
        ).status_code
        == 409
    )
    close(client, start(client, case, "print"), supply_consumptions=consume(case))
    for key in ("sand", "wait"):
        close(client, start(client, case, key))
    final_run = start(client, case, "pack")
    bad = {
        "good_quantity": "2",
        "supply_consumptions": consume(case),
        "product_consumptions": [{"variant_id": case["component"], "consumed": "3"}],
    }
    assert (
        client.post(f"/api/v1/production-runs/{final_run}/close", json=bad).status_code
        == 409
    )
    assert (
        client.get(f"/api/v1/production-runs/{final_run}").json()["status"] == "running"
    )
    assert len(client.get(f"/api/v1/supplies/{case['supply']}/movements").json()) == 2
    close(
        client,
        final_run,
        product_consumptions=[{"variant_id": case["component"], "consumed": "2"}],
    )


def test_machine_exclusivity_with_normal_runs_and_legacy(client: TestClient) -> None:
    case = setup(client)
    task = new_task(client, case["printer"])
    normal = start_normal(client, task)
    endpoint = f"{ROOT}/{case['record']['id']}/steps/print/runs"
    assert client.post(endpoint, json={"request_id": str(uuid4())}).status_code == 409
    close(client, normal, good_quantity="0")
    run = start(client, case, "print")
    assert (
        client.post(
            f"/api/v1/production-tasks/{task}/runs", json={"request_id": str(uuid4())}
        ).status_code
        == 409
    )
    legacy = new_task(client, case["printer"])
    mark_legacy(legacy)
    assert client.post(f"/api/v1/production-tasks/{legacy}/start").status_code == 409
    close(client, run, good_quantity="0")
    assert client.post(f"/api/v1/production-tasks/{legacy}/start").status_code == 200
    assert client.post(endpoint, json={"request_id": str(uuid4())}).status_code == 409
    assert client.post(f"/api/v1/production-tasks/{legacy}/pause").status_code == 200
    retry = start(client, case, "print")
    assert client.post(f"/api/v1/production-tasks/{legacy}/resume").status_code == 409
    close(client, retry, good_quantity="0")


def test_concurrent_start_close_and_promotion_are_idempotent(
    client: TestClient,
) -> None:
    case = setup(client)
    root = f"{ROOT}/{case['record']['id']}"
    request = {"request_id": str(uuid4())}
    with ThreadPoolExecutor(max_workers=2) as pool:
        starts = list(
            pool.map(
                lambda _: client.post(root + "/steps/print/runs", json=request),
                range(2),
            )
        )
    assert [item.status_code for item in starts] == [201, 201]
    assert starts[0].json()["id"] == starts[1].json()["id"]
    run = starts[0].json()["id"]
    result = {"good_quantity": "4", "supply_consumptions": consume(case)}
    with ThreadPoolExecutor(max_workers=2) as pool:
        closes = list(
            pool.map(
                lambda _: client.post(
                    f"/api/v1/production-runs/{run}/close", json=result
                ),
                range(2),
            )
        )
    assert [item.status_code for item in closes] == [200, 200]
    assert len(client.get(f"/api/v1/supplies/{case['supply']}/movements").json()) == 1
    for key in ("sand", "wait"):
        close(client, start(client, case, key))
    close(
        client,
        start(client, case, "pack"),
        product_consumptions=[{"variant_id": case["component"], "consumed": "2"}],
    )
    promotion = {"request_id": str(uuid4()), "quantity": "2"}
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda _: client.post(root + "/promote", json=promotion), range(2))
        )
    assert [item.status_code for item in results] == [201, 201]
    assert results[0].json()["id"] == results[1].json()["id"]
    assert stock(client, case["payload"]["variant_id"]) == 2


def test_close_commit_failure_rolls_back_consumptions(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = setup(client)
    run = start(client, case, "print")
    with SessionFactory() as session:

        def fail() -> None:
            raise SQLAlchemyError("simulated commit failure")

        monkeypatch.setattr(session, "commit", fail)
        with pytest.raises(PersistenceError):
            PrintService(session).close_run(
                UUID(run),
                RunClose.model_validate(
                    {"good_quantity": "2", "supply_consumptions": consume(case)}
                ),
            )
    assert client.get(f"/api/v1/production-runs/{run}").json()["status"] == "running"
    assert client.get(f"/api/v1/supplies/{case['supply']}/movements").json() == []
    close(client, run, supply_consumptions=consume(case))


def test_cancel_invalid_quantities_scoping_and_machine_validation(
    client: TestClient,
) -> None:
    case = setup(client)
    root = f"{ROOT}/{case['record']['id']}"
    assert (
        client.post(ROOT, json={**case["payload"], "target_quantity": "3"}).status_code
        == 409
    )
    assert (
        client.post(
            ROOT,
            json={
                **case["payload"],
                "request_id": str(uuid4()),
                "target_quantity": "1.5",
            },
        ).status_code
        == 409
    )
    _, other = product(client)
    assert (
        client.post(
            ROOT,
            json={**case["payload"], "request_id": str(uuid4()), "variant_id": other},
        ).status_code
        == 409
    )
    assert (
        client.post(
            root + "/steps/unknown/runs", json={"request_id": str(uuid4())}
        ).status_code
        == 404
    )
    assert (
        client.post(
            root + "/steps/print/runs",
            json={"request_id": str(uuid4()), "machine_id": None},
        ).status_code
        == 409
    )
    run = start(client, case, "print")
    assert client.post(root + "/cancel").status_code == 409
    assert (
        client.post(
            f"/api/v1/production-runs/{run}/close",
            json={"good_quantity": "-1", "supply_consumptions": consume(case)},
        ).status_code
        == 422
    )
    close(client, run, good_quantity="0")
    assert client.post(root + "/cancel").json()["status"] == "cancelled"
    assert client.post(root + "/cancel").status_code == 200
    assert (
        client.post(
            root + "/steps/print/runs", json={"request_id": str(uuid4())}
        ).status_code
        == 409
    )
    assert (
        client.post(
            root + "/promote", json={"request_id": str(uuid4()), "quantity": "1"}
        ).status_code
        == 409
    )
    assert (
        client.get(
            ROOT, params={"variant_id": case["payload"]["variant_id"], "limit": 1}
        ).json()[0]["id"]
        == case["record"]["id"]
    )
    assert len(client.get(root + "/steps/print/runs").json()) == 1


def test_excess_good_output_partial_promotion_and_external_components(
    client: TestClient,
) -> None:
    case = setup(client)
    _, external = product(client)
    close(
        client,
        start(client, case, "print"),
        good_quantity="4",
        supply_consumptions=consume(case),
    )
    for key in ("sand", "wait"):
        close(client, start(client, case, key))
    final_run = start(client, case, "pack")
    result = close(
        client,
        final_run,
        good_quantity="3",
        product_consumptions=[
            {"variant_id": case["component"], "consumed": "3"},
            {"variant_id": external, "consumed": "1"},
        ],
    )
    assert stock(client, external) == -1
    assert result["warnings"] == ["insufficient_product_stock:" + external]
    root = f"{ROOT}/{case['record']['id']}"
    assert (
        client.post(
            root + "/promote", json={"request_id": str(uuid4()), "quantity": "4"}
        ).status_code
        == 409
    )
    promoted = client.post(
        root + "/promote", json={"request_id": str(uuid4()), "quantity": "2"}
    )
    assert promoted.status_code == 201, promoted.text
    assert stock(client, case["payload"]["variant_id"]) == 2
    assert stock(client, case["component"]) == 0
    with SessionFactory() as session:
        assert (
            session.scalar(select(func.count()).select_from(ProductStockMovement)) == 2
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(ProductionRun)
                .where(ProductionRun.task_id.is_not(None))
            )
            == 0
        )
