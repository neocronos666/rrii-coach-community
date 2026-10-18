from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, IntegrityError, SQLAlchemyError

from app.db.engine import engine
from app.db.exceptions import PersistenceError
from app.db.session import SessionFactory
from app.modules.production.run_exceptions import RunConflictError
from app.modules.production.run_models import ProductionRun
from app.modules.production.test_print_schemas import TestPrintPromotion as Promotion
from app.modules.production.test_print_service import TestPrintService as PrintService
from app.modules.products.models import ProductVariant
from app.modules.products.stock_models import ProductStockMovement
from tests.integration import test_hito10b_options as catalog
from tests.integration.test_hito9_recipes import setup_recipe
from tests.integration.test_hito9_runs import new_task
from tests.integration.test_hito9_runs import start as start_normal
from tests.integration.test_hito10b_base_recipe import product
from tests.integration.test_hito10b_recipe_conditions import save
from tests.integration.test_hito10b_test_print import (
    ROOT,
    close,
    consume,
    finish,
    setup,
    start,
    stock,
)

pytestmark = pytest.mark.integration
client = catalog.client


def test_promotion_refreshes_locked_variant_in_reused_session(
    client: TestClient,
) -> None:
    case = setup(client)
    finish(client, case)
    with SessionFactory() as session:
        cached = session.get(ProductVariant, UUID(case["payload"]["variant_id"]))
        assert cached is not None and cached.active
        response = client.patch(
            f"/api/v1/product-variants/{cached.id}", json={"active": False}
        )
        assert response.status_code == 200, response.text
        with pytest.raises(RunConflictError, match="inactiva"):
            PrintService(session).promote(
                UUID(case["record"]["id"]),
                Promotion(request_id=uuid4(), quantity=Decimal("2")),
            )
    assert stock(client, case["payload"]["variant_id"]) == 0


def test_concurrent_creation_and_mixed_machine_claim(client: TestClient) -> None:
    case = setup(client)
    payload = {**case["payload"], "request_id": str(uuid4())}
    with ThreadPoolExecutor(max_workers=2) as pool:
        created = list(pool.map(lambda _: client.post(ROOT, json=payload), range(2)))
    assert [response.status_code for response in created] == [201, 201]
    assert created[0].json()["id"] == created[1].json()["id"]
    task = new_task(client, case["printer"])
    endpoints = [
        f"{ROOT}/{case['record']['id']}/steps/print/runs",
        f"/api/v1/production-tasks/{task}/runs",
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        claimed = list(
            pool.map(
                lambda endpoint: client.post(
                    endpoint, json={"request_id": str(uuid4())}
                ),
                endpoints,
            )
        )
    assert sorted(response.status_code for response in claimed) == [201, 409]
    run = next(
        response.json()["id"] for response in claimed if response.status_code == 201
    )
    close(client, run, good_quantity="0")


def test_wasted_internal_components_can_be_replenished_without_commercial_stock(
    client: TestClient,
) -> None:
    case = setup(client)
    close(client, start(client, case, "print"), supply_consumptions=consume(case))
    for key in ("sand", "wait"):
        close(client, start(client, case, key))
    close(
        client,
        start(client, case, "pack"),
        good_quantity="0",
        failed_quantity="2",
        product_consumptions=[
            {
                "variant_id": case["component"],
                "consumed": "2",
                "wasted": "2",
            }
        ],
    )
    run = start(client, case, "pack")
    request = {
        "good_quantity": "2",
        "product_consumptions": [{"variant_id": case["component"], "consumed": "2"}],
    }
    assert (
        client.post(f"/api/v1/production-runs/{run}/close", json=request).status_code
        == 409
    )
    close(client, start(client, case, "print"), supply_consumptions=consume(case))
    assert (
        client.post(f"/api/v1/production-runs/{run}/close", json=request).status_code
        == 200
    )
    result = client.get(f"{ROOT}/{case['record']['id']}").json()
    assert result["status"] == "completed"
    assert Decimal(result["promotable_quantity"]) == 2
    assert stock(client, case["component"]) == 0
    assert len(client.get(f"/api/v1/supplies/{case['supply']}/movements").json()) == 2


def test_shared_internal_components_cannot_be_spent_by_another_test(
    client: TestClient,
) -> None:
    case = setup(client)
    close(
        client,
        start(client, case, "print"),
        good_quantity="10",
        supply_consumptions=consume(case),
    )
    other = {
        **case,
        "record": client.post(
            ROOT, json={**case["payload"], "request_id": str(uuid4())}
        ).json(),
    }
    close(client, start(client, other, "print"), supply_consumptions=consume(case))
    for key in ("sand", "wait"):
        close(client, start(client, other, key))
    run = start(client, other, "pack")
    response = client.post(
        f"/api/v1/production-runs/{run}/close",
        json={
            "good_quantity": "3",
            "product_consumptions": [
                {"variant_id": case["component"], "consumed": "3"}
            ],
        },
    )
    assert response.status_code == 409
    assert stock(client, case["component"]) == 0


def test_promotion_commit_failure_and_request_collision_preserve_stock(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = setup(client)
    finish(client, case)
    payload = Promotion(request_id=uuid4(), quantity=Decimal("2"))
    with SessionFactory() as session:

        def fail() -> None:
            raise SQLAlchemyError("simulated commit failure")

        monkeypatch.setattr(session, "commit", fail)
        with pytest.raises(PersistenceError):
            PrintService(session).promote(UUID(case["record"]["id"]), payload)
    assert stock(client, case["payload"]["variant_id"]) == 0
    manual = client.post(
        f"/api/v1/product-variants/{case['payload']['variant_id']}/stock-movements",
        json={
            "request_id": str(payload.request_id),
            "quantity": "1",
            "movement_type": "purchase",
            "reason": "Compra",
        },
    )
    assert manual.status_code == 201
    assert (
        client.post(
            f"{ROOT}/{case['record']['id']}/promote",
            json=payload.model_dump(mode="json"),
        ).status_code
        == 409
    )
    assert stock(client, case["payload"]["variant_id"]) == 1
    assert (
        client.get(f"{ROOT}/{case['record']['id']}").json()["promotion_movement_id"]
        is None
    )


def test_legacy_recipe_and_fractional_service_demand(client: TestClient) -> None:
    recipe, variant = setup_recipe(client)
    save(
        client,
        recipe,
        [
            {"key": "prepare", "title": "Preparar", "quantity_per_output": "0.25"},
            {
                "key": "make",
                "title": "Fabricar",
                "output_variant_id": variant,
                "depends_on": ["prepare"],
            },
        ],
    )
    response = client.post(
        ROOT,
        json={
            "request_id": str(uuid4()),
            "recipe_id": recipe,
            "variant_id": variant,
            "target_quantity": "2",
        },
    )
    assert response.status_code == 201, response.text
    case = {"record": response.json()}
    close(client, start(client, case, "prepare"), good_quantity="0.5")
    close(client, start(client, case, "make"))
    assert client.get(f"{ROOT}/{case['record']['id']}").json()["status"] == "completed"
    assert stock(client, variant) == 0


def test_migration_roundtrip_preserves_existing_normal_runs_and_stock(
    client: TestClient,
) -> None:
    task = new_task(client)
    run = start_normal(client, task)
    result = close(client, run)
    _, variant = product(client)
    movement = client.post(
        f"/api/v1/product-variants/{variant}/stock-movements",
        json={
            "request_id": str(uuid4()),
            "movement_type": "purchase",
            "quantity": "3",
            "reason": "Anterior",
        },
    ).json()
    config = Config("alembic.ini")
    try:
        command.downgrade(config, "20260925_0033")
        with engine.connect() as connection:
            assert (
                MigrationContext.configure(connection).get_current_revision()
                == "20260925_0033"
            )
    finally:
        command.upgrade(config, "head")
    assert client.get(f"/api/v1/production-runs/{run}").json() == result
    assert client.get(f"/api/v1/product-variants/{variant}/stock-movements").json() == [
        movement
    ]


def test_migration_guard_and_database_origin_constraints(client: TestClient) -> None:
    case = setup(client)
    config = Config("alembic.ini")
    with pytest.raises(DBAPIError, match="Pruebas existentes"):
        command.downgrade(config, "20260925_0033")
    with engine.connect() as connection:
        assert (
            MigrationContext.configure(connection).get_current_revision()
            == ScriptDirectory.from_config(config).get_current_head()
        )
    run_id = start(client, case, "print")
    with SessionFactory() as session:
        run = session.get(ProductionRun, UUID(run_id))
        assert run is not None
        run.test_print_step_id = None
        with pytest.raises(IntegrityError, match="origin_xor"):
            session.flush()
        session.rollback()
    close(client, run_id, supply_consumptions=consume(case))
    for key in ("sand", "wait"):
        close(client, start(client, case, key))
    close(
        client,
        start(client, case, "pack"),
        product_consumptions=[{"variant_id": case["component"], "consumed": "2"}],
    )
    promoted = client.post(
        f"{ROOT}/{case['record']['id']}/promote",
        json={"request_id": str(uuid4()), "quantity": "2"},
    )
    assert promoted.status_code == 201
    with SessionFactory() as session:
        movement = session.scalar(
            select(ProductStockMovement).where(
                ProductStockMovement.id == UUID(promoted.json()["id"])
            )
        )
        assert movement is not None
        movement.test_print_id = None
        with pytest.raises(IntegrityError, match="origin_valid"):
            session.flush()
        session.rollback()
