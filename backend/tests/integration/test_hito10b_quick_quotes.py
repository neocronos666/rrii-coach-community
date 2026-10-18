from concurrent.futures import ThreadPoolExecutor
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import SessionFactory
from app.modules.quick_quotes.models import QuickQuote, QuickQuoteRevision
from tests.integration import test_hito10b_options as catalog
from tests.integration.test_hito10b_pricing_preview import counts, purchase, setup

pytestmark = pytest.mark.integration
client = catalog.client
ROOT = "/api/v1/quick-quotes"


def definition(client: TestClient) -> tuple[str, dict[str, Any]]:
    supply, pricing = setup(client)
    purchase(client, supply, "20", "40", 1)
    return supply, {
        "request_id": str(uuid4()),
        "title": "Trabajo rápido",
        "notes": "Revisar entrega",
        "pricing": pricing,
    }


def create(client: TestClient, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post(ROOT, json=payload)
    assert response.status_code == 201, response.text
    return dict(response.json())


def commercial_counts() -> dict[str, int]:
    return {
        name: count
        for name, count in counts().items()
        if name not in {"quick_quotes", "quick_quote_revisions"}
    }


def test_create_matches_preview_and_reads_do_not_recalculate(
    client: TestClient,
) -> None:
    supply, payload = definition(client)
    preview = client.post("/api/v1/pricing-preview", json=payload["pricing"]).json()
    before = commercial_counts()
    record = create(client, payload)
    assert record["revision"] == 1
    assert record["evaluation"]["preview"] == preview
    assert record["evaluation"]["configuration"] is not None
    assert record["evaluation"]["plan"]["steps"][0]["key"] == "make"
    assert commercial_counts() == before
    purchase(client, supply, "20", "200", 2)
    assert client.get(f"{ROOT}/{record['id']}").json() == record
    assert client.get(ROOT).json() == [record]
    assert client.get(f"{ROOT}/{record['id']}/revisions/1").json() == record
    assert client.post(ROOT, json=payload).json() == record
    conflict = client.post(ROOT, json={**payload, "title": "Otro"})
    assert conflict.status_code == 409


def test_replace_recalculate_history_and_old_revision_retry(client: TestClient) -> None:
    supply, payload = definition(client)
    payload["pricing"]["strategy"] = "last_purchase"
    original = create(client, payload)
    quote_id = original["id"]
    purchase(client, supply, "20", "200", 2)
    recalculation = {"request_id": str(uuid4()), "expected_revision": 1}
    response = client.post(f"{ROOT}/{quote_id}/recalculate", json=recalculation)
    assert response.status_code == 200, response.text
    second = response.json()
    assert second["revision"] == 2
    assert second["evaluation"]["preview"]["totals_by_currency"] == {"ARS": "120.0000"}
    assert original["evaluation"]["preview"]["totals_by_currency"] == {"ARS": "24.0000"}
    replacement = {
        **payload,
        "request_id": str(uuid4()),
        "expected_revision": 2,
        "title": "Ajustado",
        "notes": None,
        "pricing": {**payload["pricing"], "target_quantity": "3"},
    }
    response = client.put(f"{ROOT}/{quote_id}", json=replacement)
    assert response.status_code == 200, response.text
    third = response.json()
    assert third["revision"] == 3
    assert third["evaluation"]["preview"]["totals_by_currency"] == {"ARS": "30.0000"}
    assert third["definition"]["notes"] is None
    assert client.get(f"{ROOT}/{quote_id}/revisions").json() == [
        third,
        second,
        original,
    ]
    assert (
        client.post(f"{ROOT}/{quote_id}/recalculate", json=recalculation).json()
        == second
    )
    assert client.post(ROOT, json=payload).json() == original
    assert client.get(f"{ROOT}/{quote_id}").json() == third
    stale = client.put(
        f"{ROOT}/{quote_id}", json={**replacement, "request_id": str(uuid4())}
    )
    assert stale.status_code == 409
    assert client.get(f"{ROOT}/{quote_id}/revisions?limit=1&offset=1").json() == [
        second
    ]


def test_incomplete_multicurrency_and_missing_markup_can_be_saved(
    client: TestClient,
) -> None:
    supply, payload = definition(client)
    payload["pricing"]["target_quantity"] = "25"
    payload["pricing"].pop("markup_percentage")
    payload["pricing"]["step_estimates"] = {}
    purchase(client, supply, "2", "4", 2, "USD")
    record = create(client, payload)
    preview = record["evaluation"]["preview"]
    assert not preview["complete"] and preview["multi_currency"]
    assert preview["markup_percentage"] is None and preview["suggested_price"] is None


def test_history_survives_catalog_change_and_retry_ignores_catalog(
    client: TestClient,
) -> None:
    _, payload = definition(client)
    record = create(client, payload)
    product_id = record["evaluation"]["product_id"]
    response = client.patch(
        f"/api/v1/products/{product_id}", json={"name": "Otro nombre", "active": False}
    )
    assert response.status_code == 200, response.text
    assert client.get(f"{ROOT}/{record['id']}").json() == record
    assert client.post(ROOT, json=payload).json() == record
    before = counts()
    response = client.post(
        f"{ROOT}/{record['id']}/recalculate",
        json={"request_id": str(uuid4()), "expected_revision": 1},
    )
    assert response.status_code == 409
    assert counts() == before
    assert client.get(f"{ROOT}/{record['id']}/revisions").json() == [record]


def test_concurrent_creation_and_edit_conflict(client: TestClient) -> None:
    _, payload = definition(client)
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda _: client.post(ROOT, json=payload), range(4)))
    assert [response.status_code for response in responses] == [201] * 4
    records = [response.json() for response in responses]
    assert all(record == records[0] for record in records)
    quote_id = records[0]["id"]
    edits = [
        {
            **payload,
            "request_id": str(uuid4()),
            "expected_revision": 1,
            "title": f"Edición {index}",
        }
        for index in range(2)
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(lambda edit: client.put(f"{ROOT}/{quote_id}", json=edit), edits)
        )
    assert sorted(response.status_code for response in responses) == [200, 409]
    assert len(client.get(f"{ROOT}/{quote_id}/revisions").json()) == 2


def test_request_id_cannot_cross_drafts_or_operations(client: TestClient) -> None:
    _, payload = definition(client)
    original = create(client, payload)
    other = create(client, {**payload, "request_id": str(uuid4())})
    body = {"request_id": payload["request_id"], "expected_revision": 1}
    assert (
        client.post(f"{ROOT}/{other['id']}/recalculate", json=body).status_code == 409
    )
    assert (
        client.post(f"{ROOT}/{original['id']}/recalculate", json=body).status_code
        == 409
    )
    assert client.get(f"{ROOT}/{uuid4()}").status_code == 404
    assert client.get(f"{ROOT}/{original['id']}/revisions/99").status_code == 404
    assert client.get(f"{ROOT}?limit=101").status_code == 422


def test_failed_revision_rolls_back_root_and_history(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, payload = definition(client)
    original = create(client, payload)
    flush = Session.flush

    def failing_flush(self: Session, *args: Any, **kwargs: Any) -> None:
        if any(isinstance(item, QuickQuoteRevision) for item in self.new):
            raise SQLAlchemyError("Fallo simulado al guardar revisión")
        flush(self, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Session, "flush", failing_flush)
        response = client.put(
            f"{ROOT}/{original['id']}",
            json={
                **payload,
                "request_id": str(uuid4()),
                "expected_revision": 1,
                "title": "No guardar",
            },
        )
        assert response.status_code == 500
        response = client.post(ROOT, json={**payload, "request_id": str(uuid4())})
        assert response.status_code == 500
    assert client.get(ROOT).json() == [original]
    with SessionFactory() as session:
        assert len(list(session.scalars(select(QuickQuote)))) == 1
        assert len(list(session.scalars(select(QuickQuoteRevision)))) == 1


def test_migration_roundtrip_and_guard(client: TestClient) -> None:
    from alembic import command
    from alembic.config import Config
    from alembic.migration import MigrationContext
    from alembic.script import ScriptDirectory

    from app.db.engine import engine

    _, payload = definition(client)
    before = commercial_counts()
    config = Config("alembic.ini")
    try:
        command.downgrade(config, "20260928_0035")
    finally:
        command.upgrade(config, "head")
    assert commercial_counts() == before
    record = create(client, payload)
    with pytest.raises(RuntimeError, match="historia de Quick Quote"):
        command.downgrade(config, "20260928_0035")
    with engine.connect() as connection:
        assert (
            MigrationContext.configure(connection).get_current_revision()
            == ScriptDirectory.from_config(config).get_current_head()
        )
    assert client.get(f"{ROOT}/{record['id']}").json() == record


def test_effective_context_frozen_and_recalculation_retry(client: TestClient) -> None:
    from sqlalchemy import update

    from app.modules.products.models import Product
    from tests.integration.test_hito10b_test_print import setup as setup_print

    case = setup_print(client)
    pricing = {
        key: value
        for key, value in case["payload"].items()
        if key not in {"request_id", "machine_assignments"}
    }
    original = create(
        client,
        {"request_id": str(uuid4()), "title": "Con opciones", "pricing": pricing},
    )
    snapshot = original["evaluation"]
    assert snapshot["configuration"] is not None
    assert snapshot["preview"]["omitted_step_keys"] == ["paint"]
    assert snapshot["plan"]["steps"][0]["resources"]
    with SessionFactory() as session:
        session.execute(update(Product).values(name="Nombre actual"))
        session.commit()
    assert client.get(f"{ROOT}/{original['id']}").json() == original
    request = {"request_id": str(uuid4()), "expected_revision": 1}
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(
                lambda _: client.post(
                    f"{ROOT}/{original['id']}/recalculate", json=request
                ),
                range(2),
            )
        )
    assert [response.status_code for response in responses] == [200, 200]
    assert responses[0].json() == responses[1].json()
    refreshed = responses[0].json()
    assert refreshed["revision"] == 2
    assert refreshed["evaluation"]["product_name"] == "Nombre actual"
    assert original["evaluation"]["product_name"] != "Nombre actual"
    assert client.get(f"{ROOT}/{original['id']}/revisions/1").json() == original
    assert len(client.get(f"{ROOT}/{original['id']}/revisions").json()) == 2
