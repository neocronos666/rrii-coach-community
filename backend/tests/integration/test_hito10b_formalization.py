from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import SessionFactory
from app.modules.products.models import Product
from app.modules.quick_quotes.formalization_models import QuickQuoteFormalization
from tests.integration import test_hito10b_options as catalog
from tests.integration.test_hito10b_base_recipe import final
from tests.integration.test_hito10b_pricing_preview import counts
from tests.integration.test_hito10b_quick_quotes import create, definition
from tests.integration.test_hito10b_recipe_conditions import save

pytestmark = pytest.mark.integration
client = catalog.client
ROOT = "/api/v1/quick-quotes"


def draft(client: TestClient) -> dict[str, Any]:
    _, payload = definition(client)
    save(client, payload["pricing"]["recipe_id"], [final(batch_yield="4")])
    payload["pricing"].update(
        target_quantity="3",
        markup_percentage="0",
        step_estimates={
            "make": {
                "extras": [
                    {"description": "Preparación", "amount": "1", "currency": "ARS"}
                ]
            }
        },
    )
    return create(client, payload)


def formalize(
    client: TestClient, record: dict[str, Any], **changes: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = {
        "request_id": str(uuid4()),
        "source_revision": record["revision"],
        **changes,
    }
    response = client.post(f"{ROOT}/{record['id']}/formalize", json=payload)
    assert response.status_code == 201, response.text
    return dict(response.json()), payload


def test_total_quantity_snapshot_and_commercial_edit(client: TestClient) -> None:
    record = draft(client)
    before = counts()
    bridge, payload = formalize(client, record, final_price="1.87")
    quote = client.get(f"/api/v1/quotes/{bridge['quote_id']}").json()
    assert quote["status"] == "draft"
    assert bridge["source_revision"] == 1
    assert quote["source_quick_quote_id"] == record["id"]
    assert quote["source_quick_quote_revision"] == 1
    assert Decimal(quote["items"][0]["quantity"]) == 3
    assert Decimal(quote["items"][0]["technical_unit_cost"]) == Decimal("0.3333")
    assert Decimal(quote["items"][0]["technical_total_cost"]) == 1
    assert Decimal(quote["breakdown"]["technical_cost"]) == 1
    assert Decimal(quote["breakdown"]["final_price"]) == 1
    calculation = client.get(
        f"/api/v1/cost-calculations/{bridge['cost_calculation_id']}"
    ).json()
    assert calculation["calculation_type"] == "recipe_demand"
    assert Decimal(calculation["demand_quantity"]) == 3
    assert calculation["demand_unit"] == "unit"
    assert calculation["totals_by_currency"] == {"ARS": "1.0000"}
    assert calculation["calculated_at"] == record["created_at"]
    after = counts()
    for table, count in before.items():
        if table not in {
            "quotes",
            "quote_items",
            "cost_calculations",
            "cost_calculation_lines",
            "quick_quote_formalizations",
        }:
            assert after[table] == count, table
    response = client.patch(
        f"/api/v1/quotes/{bridge['quote_id']}",
        json={
            "title": "Oferta final",
            "markup_percentage": "20",
            "final_price": "1.50",
        },
    )
    assert response.status_code == 200, response.text
    edited = response.json()
    assert Decimal(edited["breakdown"]["technical_cost"]) == 1
    assert Decimal(edited["items"][0]["quantity"]) == 3
    assert Decimal(edited["breakdown"]["suggested_price"]) == Decimal("1.2")
    assert Decimal(edited["breakdown"]["final_price"]) == Decimal("1")
    assert (
        client.post(f"{ROOT}/{record['id']}/formalize", json=payload).json() == bridge
    )
    assert client.get(f"{ROOT}/{record['id']}/formalization").json() == bridge
    assert client.get(f"{ROOT}/{record['id']}").json() == record
    assert (
        client.post(f"/api/v1/quotes/{bridge['quote_id']}/convert").status_code == 409
    )
    assert (
        client.post(f"/api/v1/quotes/{bridge['quote_id']}/approve").status_code == 200
    )
    converted = client.post(f"/api/v1/quotes/{bridge['quote_id']}/convert")
    assert converted.status_code == 201, converted.text
    order = client.get(f"/api/v1/orders/{converted.json()['target_id']}").json()
    assert Decimal(order["quantity"]) == 3
    assert Decimal(order["technical_total_cost"]) == 1
    assert Decimal(order["quoted_final_price"]) == 1
    assert (
        client.patch(
            f"/api/v1/quotes/{bridge['quote_id']}", json={"title": "No"}
        ).status_code
        == 409
    )


def test_snapshot_formalized_without_live_catalog_and_only_once(
    client: TestClient,
) -> None:
    record = draft(client)
    recalc = client.post(
        f"{ROOT}/{record['id']}/recalculate",
        json={"request_id": str(uuid4()), "expected_revision": 1},
    )
    assert recalc.status_code == 200
    with SessionFactory() as session:
        session.execute(update(Product).values(active=False, name="Ahora inactivo"))
        session.commit()
    bridge, payload = formalize(client, record)
    assert (
        client.post(f"{ROOT}/{record['id']}/formalize", json=payload).json() == bridge
    )
    assert (
        client.post(
            f"{ROOT}/{record['id']}/formalize",
            json={**payload, "request_id": str(uuid4()), "source_revision": 2},
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"{ROOT}/{record['id']}/formalize", json={**payload, "title": "Distinto"}
        ).status_code
        == 409
    )
    with SessionFactory() as session:
        link = session.scalar(select(QuickQuoteFormalization))
        assert link is not None and link.quick_quote_id == UUID(record["id"])


def test_demand_items_cannot_be_scaled_replaced_or_reused(client: TestClient) -> None:
    record = draft(client)
    bridge, _ = formalize(client, record)
    path = f"/api/v1/quotes/{bridge['quote_id']}"
    item = {
        "description": record["definition"]["title"],
        "quantity": "3",
        "cost_calculation_id": bridge["cost_calculation_id"],
    }
    assert client.patch(path, json={"items": [item]}).status_code == 200
    assert (
        client.patch(path, json={"items": [{**item, "quantity": "6"}]}).status_code
        == 409
    )
    assert (
        client.post(
            "/api/v1/quotes", json={"title": "Duplicado", "items": [item]}
        ).status_code
        == 422
    )
    ordinary = client.post(
        "/api/v1/cost-calculations",
        json={"extras": [{"description": "Otro", "amount": "2", "currency": "ARS"}]},
    ).json()
    assert (
        client.patch(
            path, json={"items": [{**item, "cost_calculation_id": ordinary["id"]}]}
        ).status_code
        == 409
    )


@pytest.mark.parametrize("case", ["incomplete", "missing_markup", "multi_currency"])
def test_invalid_economy_has_no_partial_writes(client: TestClient, case: str) -> None:
    _, payload = definition(client)
    if case == "incomplete":
        payload["pricing"]["step_estimates"] = {}
    elif case == "missing_markup":
        payload["pricing"].pop("markup_percentage")
    else:
        payload["pricing"]["step_estimates"] = {
            "make": {
                "extras": [{"description": "USD", "amount": "1", "currency": "USD"}]
            }
        }
    record = create(client, payload)
    before = counts()
    response = client.post(
        f"{ROOT}/{record['id']}/formalize",
        json={"request_id": str(uuid4()), "source_revision": 1},
    )
    assert response.status_code == 422, response.text
    assert counts() == before


def test_concurrent_requests_and_unique_quote(client: TestClient) -> None:
    record = draft(client)
    body = {"request_id": str(uuid4()), "source_revision": 1}
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(
            pool.map(
                lambda _: client.post(f"{ROOT}/{record['id']}/formalize", json=body),
                range(3),
            )
        )
    assert [result.status_code for result in results] == [201] * 3
    assert all(result.json() == results[0].json() for result in results)
    other = draft(client)
    bodies = [{"request_id": str(uuid4()), "source_revision": 1} for _ in range(2)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda item: client.post(f"{ROOT}/{other['id']}/formalize", json=item),
                bodies,
            )
        )
    assert sorted(result.status_code for result in results) == [201, 409]


def test_failure_after_quote_rolls_back_everything(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = draft(client)
    before = counts()
    flush = Session.flush

    def fail(self: Session, *args: Any, **kwargs: Any) -> None:
        if any(isinstance(item, QuickQuoteFormalization) for item in self.new):
            raise SQLAlchemyError("Fallo de vínculo simulado")
        flush(self, *args, **kwargs)

    body = {"request_id": str(uuid4()), "source_revision": 1}
    with monkeypatch.context() as patch:
        patch.setattr(Session, "flush", fail)
        response = client.post(f"{ROOT}/{record['id']}/formalize", json=body)
        assert response.status_code == 500
    assert counts() == before
    assert client.post(f"{ROOT}/{record['id']}/formalize", json=body).status_code == 201


def test_migration_roundtrip_and_guard(client: TestClient) -> None:
    from alembic import command
    from alembic.config import Config
    from alembic.migration import MigrationContext
    from alembic.script import ScriptDirectory

    from app.db.engine import engine

    record = draft(client)
    before = counts()
    config = Config("alembic.ini")
    try:
        command.downgrade(config, "20260928_0036")
    finally:
        command.upgrade(config, "head")
    assert counts() == before
    bridge, _ = formalize(client, record)
    with pytest.raises(RuntimeError, match="historia de formalización"):
        command.downgrade(config, "20260928_0036")
    with engine.connect() as connection:
        assert (
            MigrationContext.configure(connection).get_current_revision()
            == ScriptDirectory.from_config(config).get_current_head()
        )
    assert client.get(f"{ROOT}/{record['id']}/formalization").json() == bridge


def test_fractional_quantity_and_commercial_terms(client: TestClient) -> None:
    from tests.integration.test_hito10b_base_recipe import base

    product = client.post(
        "/api/v1/products",
        json={
            "name": "Servicio medido",
            "initial_variant": {"name": "Metros", "base_unit": "m"},
        },
    ).json()
    recipe = base(client, product["id"])
    save(client, recipe, [final(unit="m")])
    record = create(
        client,
        {
            "request_id": str(uuid4()),
            "title": "Medido",
            "pricing": {
                "recipe_id": recipe,
                "variant_id": product["initial_variant"]["id"],
                "target_quantity": "0.3",
                "markup_percentage": "0",
                "step_estimates": {
                    "make": {
                        "extras": [
                            {"description": "Trabajo", "amount": "1", "currency": "ARS"}
                        ]
                    }
                },
            },
        },
    )
    settings = client.get("/api/v1/settings").json()
    settings.update(
        deposit_policy="required", deposit_type="percentage", deposit_value="50"
    )
    assert client.put("/api/v1/settings", json=settings).status_code == 200
    bridge, _ = formalize(
        client,
        record,
        adjustments=[
            {
                "description": "Recargo",
                "adjustment_type": "surcharge",
                "value_type": "fixed",
                "value": "1",
            }
        ],
        final_price="3",
    )
    quote = client.get(f"/api/v1/quotes/{bridge['quote_id']}").json()
    assert Decimal(quote["items"][0]["quantity"]) == Decimal("0.3")
    assert Decimal(quote["items"][0]["technical_unit_cost"]) == Decimal("3.3333")
    assert Decimal(quote["breakdown"]["technical_cost"]) == 1
    assert Decimal(quote["breakdown"]["suggested_price"]) == 2
    assert Decimal(quote["breakdown"]["deposit_amount"]) == Decimal("1.5")
    settings["deposit_value"] = "10"
    client.put("/api/v1/settings", json=settings)
    assert client.get(f"/api/v1/quotes/{bridge['quote_id']}").json() == quote


def test_cached_draft_cannot_modify_approved_quote(client: TestClient) -> None:
    from app.modules.quotes.exceptions import QuoteNotEditableError
    from app.modules.quotes.repository import QuoteRepository
    from app.modules.quotes.schemas import QuoteUpdate
    from app.modules.quotes.service import QuoteService

    bridge, _ = formalize(client, draft(client))
    quote_id = UUID(bridge["quote_id"])
    with SessionFactory() as session:
        cached = QuoteRepository(session).get(quote_id)
        assert cached is not None and cached.status == "draft"
        assert client.post(f"/api/v1/quotes/{quote_id}/approve").status_code == 200
        with pytest.raises(QuoteNotEditableError):
            QuoteService(session).update(quote_id, QuoteUpdate(title="No sobrescribir"))
        session.rollback()
    assert client.get(f"/api/v1/quotes/{quote_id}").json()["status"] == "approved"


def test_invalid_commercial_terms_roll_back(client: TestClient) -> None:
    record = draft(client)
    before = counts()
    response = client.post(
        f"{ROOT}/{record['id']}/formalize",
        json={
            "request_id": str(uuid4()),
            "source_revision": 1,
            "adjustments": [
                {
                    "description": "Excesivo",
                    "adjustment_type": "discount",
                    "value_type": "fixed",
                    "value": "2",
                }
            ],
        },
    )
    assert response.status_code == 422
    assert counts() == before
    response = client.post(
        f"{ROOT}/{uuid4()}/formalize",
        json={"request_id": str(uuid4()), "source_revision": 1},
    )
    assert response.status_code == 404
    response = client.post(
        f"{ROOT}/{record['id']}/formalize",
        json={"request_id": str(uuid4()), "source_revision": 99},
    )
    assert response.status_code == 404
    assert counts() == before
