from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update

from app.db.base import Base
from app.db.session import SessionFactory
from app.modules.supplies.models import SupplyStockMovement
from tests.integration import test_hito10b_options as catalog
from tests.integration.test_hito10b_base_recipe import base, final, product
from tests.integration.test_hito10b_recipe_conditions import save
from tests.integration.test_hito10b_selected_materials import material

pytestmark = pytest.mark.integration
client = catalog.client
ROOT = "/api/v1/pricing-preview"


def setup(client: TestClient) -> tuple[str, dict[str, Any]]:
    product_id, variant = product(client)
    recipe = base(client, product_id)
    supply = material(client)
    save(
        client,
        recipe,
        [final(supply_inputs=[{"supply_id": supply, "quantity_per_batch": "1"}])],
    )
    return supply, {
        "recipe_id": recipe,
        "variant_id": variant,
        "target_quantity": "12",
        "step_estimates": {"make": {}},
        "markup_percentage": "25",
    }


def purchase(
    client: TestClient,
    supply: str,
    qty: str,
    cost: str,
    day: int,
    currency: str = "ARS",
) -> str:
    response = client.post(
        f"/api/v1/supplies/{supply}/purchases",
        json={
            "quantity": qty,
            "total_cost": cost,
            "currency": currency,
            "purchased_at": f"2026-09-{day:02}T12:00:00Z",
        },
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def counts() -> dict[str, int]:
    with SessionFactory() as session:
        return {
            table.name: int(
                session.scalar(select(func.count()).select_from(table)) or 0
            )
            for table in Base.metadata.sorted_tables
        }


def test_fifo_read_only_and_distinct_from_latest(client: TestClient) -> None:
    supply, payload = setup(client)
    first = purchase(client, supply, "10", "20", 1)
    second = purchase(client, supply, "10", "30", 2)
    before = counts()
    response = client.post(ROOT, json=payload)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["complete"]
    assert result["totals_by_currency"] == {"ARS": "26.0000"}
    assert Decimal(result["suggested_price"]) == Decimal("32.5")
    assert [line["purchase_id"] for line in result["lines"]] == [first, second]
    assert counts() == before
    repeated = client.post(ROOT, json=payload)
    assert repeated.json() == result
    latest = client.post(ROOT, json={**payload, "strategy": "last_purchase"})
    assert latest.json()["totals_by_currency"] == {"ARS": "36.0000"}
    assert counts() == before


def test_historical_adjustment_shortage_and_missing_estimate(
    client: TestClient,
) -> None:
    supply, payload = setup(client)
    purchase(client, supply, "10", "20", 1)
    with SessionFactory() as session:
        session.execute(
            update(SupplyStockMovement)
            .where(SupplyStockMovement.supply_id == UUID(supply))
            .values(purchase_id=None)
        )
        session.commit()
    purchase(client, supply, "1", "3", 2)
    result = client.post(ROOT, json={**payload, "step_estimates": {}}).json()
    assert not result["complete"]
    assert result["suggested_price"] is None
    assert result["totals_by_currency"] == {"ARS": "3.0000"}
    assert [Decimal(line["quantity"]) for line in result["lines"][:3]] == [10, 1, 1]
    assert result["lines"][-1]["category"] == "step_estimate"


def test_multicurrency_and_retroactive_adjustment(client: TestClient) -> None:
    supply, payload = setup(client)
    purchase(client, supply, "10", "20", 2)
    purchase(client, supply, "10", "30", 1, "USD")
    result = client.post(ROOT, json=payload).json()
    assert result["complete"] and result["multi_currency"]
    assert result["totals_by_currency"] == {"USD": "30.0000", "ARS": "4.0000"}
    assert result["suggested_price"] is None
    adjustment = client.post(
        f"/api/v1/supplies/{supply}/adjustments",
        json={
            "direction": "out",
            "quantity": "5",
            "reason": "Corrección",
            "occurred_at": "2026-09-01T14:00:00Z",
        },
    )
    assert adjustment.status_code == 201, adjustment.text
    result = client.post(ROOT, json=payload).json()
    assert result["totals_by_currency"] == {"USD": "15.0000", "ARS": "14.0000"}


def test_shared_layers_and_invalid_estimates(client: TestClient) -> None:
    supply, payload = setup(client)
    save(
        client,
        payload["recipe_id"],
        [
            {
                "key": "prep",
                "title": "Preparar",
                "supply_inputs": [{"supply_id": supply, "quantity_per_batch": "1"}],
            },
            final(
                depends_on=["prep"],
                supply_inputs=[{"supply_id": supply, "quantity_per_batch": "1"}],
            ),
        ],
    )
    purchase(client, supply, "15", "30", 1)
    payload["step_estimates"]["prep"] = {}
    result = client.post(ROOT, json=payload).json()
    assert not result["complete"]
    assert result["totals_by_currency"] == {"ARS": "30.0000"}
    payload["step_estimates"]["missing"] = {}
    assert client.post(ROOT, json=payload).status_code == 409


def test_adjustment_without_cost_and_debt_replenishment(client: TestClient) -> None:
    supply, payload = setup(client)
    # Deuda histórica anterior a las compras: las entradas primero la cubren.
    from datetime import UTC, datetime

    with SessionFactory() as session:
        session.add(
            SupplyStockMovement(
                supply_id=UUID(supply),
                movement_type="adjustment_out",
                quantity=Decimal(-8),
                occurred_at=datetime(2026, 8, 1, tzinfo=UTC),
            )
        )
        session.commit()
    purchase(client, supply, "10", "20", 1)
    result = client.post(ROOT, json={**payload, "target_quantity": "3"}).json()
    assert result["totals_by_currency"] == {"ARS": "4.0000"}
    assert not result["complete"]
    adjustment = client.post(
        f"/api/v1/supplies/{supply}/adjustments",
        json={
            "direction": "in",
            "quantity": "5",
            "reason": "Sin valuación",
            "occurred_at": "2026-09-02T14:00:00Z",
        },
    )
    assert adjustment.status_code == 201
    result = client.post(ROOT, json={**payload, "target_quantity": "3"}).json()
    assert not result["complete"]
    assert result["lines"][1]["movement_id"] == adjustment.json()["id"]
    assert result["lines"][1]["purchase_id"] is None


def test_migration_preserves_unlinked_history_and_guards_links(
    client: TestClient,
) -> None:
    from alembic import command
    from alembic.config import Config
    from alembic.migration import MigrationContext
    from alembic.script import ScriptDirectory

    from app.db.engine import engine

    supply, _ = setup(client)
    purchase_id = purchase(client, supply, "10", "20", 1)
    config = Config("alembic.ini")
    with pytest.raises(RuntimeError, match="trazabilidad"):
        command.downgrade(config, "20260926_0034")
    with engine.connect() as connection:
        assert (
            MigrationContext.configure(connection).get_current_revision()
            == ScriptDirectory.from_config(config).get_current_head()
        )
    with SessionFactory() as session:
        session.execute(update(SupplyStockMovement).values(purchase_id=None))
        session.commit()
    try:
        command.downgrade(config, "20260926_0034")
    finally:
        command.upgrade(config, "head")
    movements = client.get(f"/api/v1/supplies/{supply}/movements").json()
    assert len(movements) == 1 and movements[0]["purchase_id"] is None
    purchases = client.get(f"/api/v1/supplies/{supply}/purchases").json()
    assert purchases[0]["id"] == purchase_id


def test_recipe_resolution_matches_test_print_and_external_cost_missing(
    client: TestClient,
) -> None:
    from tests.integration.test_hito10b_test_print import setup as setup_print

    case = setup_print(client)
    payload = {
        key: value
        for key, value in case["payload"].items()
        if key not in {"request_id", "machine_assignments"}
    }
    before = counts()
    response = client.post(ROOT, json=payload)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["omitted_step_keys"] == ["paint"]
    assert {step["key"] for step in result["planned_steps"]} == {
        "print",
        "sand",
        "wait",
        "pack",
    }
    assert not any(line["category"] == "component" for line in result["lines"])
    assert counts() == before
    assert (
        client.post(ROOT, json={**payload, "step_estimates": {"print": {}}}).status_code
        == 409
    )


def test_typed_labor_and_explicit_zero_markup(client: TestClient) -> None:
    supply, payload = setup(client)
    purchase(client, supply, "20", "40", 1)
    payload["step_estimates"] = {
        "make": {"labor": [{"labor_type": "assembly", "duration_minutes": 60}]}
    }
    missing = client.post(ROOT, json=payload).json()
    assert not missing["complete"] and missing["suggested_price"] is None
    settings = client.get("/api/v1/settings").json()
    settings["assembly_hour_rate"] = "10"
    settings["default_markup_percentage"] = "30"
    assert client.put("/api/v1/settings", json=settings).status_code == 200
    result = client.post(ROOT, json={**payload, "markup_percentage": "0"}).json()
    assert result["complete"]
    assert Decimal(result["suggested_price"]) == Decimal("34")


def test_purchase_normalized_link_and_rollback(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sqlalchemy.exc import SQLAlchemyError

    from app.modules.supplies.repository import StockMovementRepository

    supply, _ = setup(client)
    presentation = client.post(
        f"/api/v1/supplies/{supply}/presentations",
        json={"name": "Bolsa", "quantity": "1000", "unit": "g"},
    )
    assert presentation.status_code == 201
    response = client.post(
        f"/api/v1/supplies/{supply}/purchases",
        json={
            "quantity": "2",
            "presentation_id": presentation.json()["id"],
            "total_cost": "100",
            "currency": "ARS",
            "purchased_at": "2026-09-01T12:00:00Z",
        },
    )
    assert response.status_code == 201
    movement = client.get(f"/api/v1/supplies/{supply}/movements").json()[0]
    assert movement["purchase_id"] == response.json()["id"]
    assert Decimal(movement["quantity"]) == Decimal(response.json()["quantity"]) == 2000
    before = counts()

    def fail(*args: Any, **kwargs: Any) -> None:
        raise SQLAlchemyError("Fallo de ledger simulado")

    monkeypatch.setattr(StockMovementRepository, "add", fail)
    response = client.post(
        f"/api/v1/supplies/{supply}/purchases",
        json={
            "quantity": "1",
            "total_cost": "1",
            "currency": "ARS",
            "purchased_at": "2026-09-02T12:00:00Z",
        },
    )
    assert response.status_code == 500
    assert counts() == before


def test_machine_estimates_and_external_components(client: TestClient) -> None:
    from tests.integration.test_hito10b_machine_assignment import machine

    supply, payload = setup(client)
    purchase(client, supply, "20", "40", 1)
    _, component = product(client)
    save(
        client,
        payload["recipe_id"],
        [
            final(
                task_type="fdm_print",
                product_inputs=[
                    {"product_variant_id": component, "quantity_per_batch": "1"}
                ],
            )
        ],
    )
    printer = machine(client, "FDM")
    payload["step_estimates"] = {
        "make": {"machine_id": printer, "machine_duration_minutes": 60}
    }
    response = client.post(ROOT, json=payload)
    assert response.status_code == 200, response.text
    result = response.json()
    assert not result["complete"]
    assert {line["category"] for line in result["lines"]} == {
        "component",
        "machine_time",
        "energy",
    }
    payload["step_estimates"]["make"]["machine_id"] = machine(
        client, "SLA", kind="sla_printer"
    )
    assert client.post(ROOT, json=payload).status_code == 409
