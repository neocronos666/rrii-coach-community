import re
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.session import SessionFactory
from app.main import app
from app.modules.costing.models import CostCalculation, CostCalculationLine
from app.modules.orders.models import Order
from app.modules.projects.models import Project, ProjectComponent
from app.modules.quotes.conversion_models import QuoteConversion
from app.modules.quotes.models import Quote, QuoteAdjustment, QuoteItem
from app.modules.supplies.models import (
    Supply,
    SupplyPresentation,
    SupplyPurchase,
    SupplyStockMovement,
)

pytestmark = pytest.mark.integration


def clean(session: Session) -> None:
    session.execute(delete(QuoteConversion))
    session.execute(delete(ProjectComponent))
    session.execute(delete(Project))
    session.execute(delete(Order))
    session.execute(delete(QuoteAdjustment))
    session.execute(delete(QuoteItem))
    session.execute(delete(Quote))
    session.execute(delete(CostCalculationLine))
    session.execute(delete(CostCalculation))
    session.execute(delete(SupplyStockMovement))
    session.execute(delete(SupplyPurchase))
    session.execute(delete(SupplyPresentation))
    session.execute(delete(Supply))
    session.commit()


@pytest.fixture(autouse=True)
def clean_conversion_data() -> Iterator[None]:
    with SessionFactory() as session:
        clean(session)
    yield
    with SessionFactory() as session:
        clean(session)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def create_calculation(amount: str) -> str:
    with SessionFactory() as session:
        calculation = CostCalculation(
            calculation_type="technical",
            complete=True,
            multi_currency=False,
            warnings=[],
            calculated_at=datetime.now(UTC),
            lines=[
                CostCalculationLine(
                    position=0,
                    category="material",
                    description="Snapshot técnico",
                    quantity=Decimal("1"),
                    unit="unit",
                    unit_cost=Decimal(amount),
                    currency="ARS",
                    subtotal=Decimal(amount),
                    source="test",
                    source_reference="hito7",
                    complete=True,
                )
            ],
        )
        session.add(calculation)
        session.commit()
        return str(calculation.id)


def create_quote(
    client: TestClient,
    amounts: list[str],
    *,
    quantities: list[str] | None = None,
    final_price: str | None = None,
) -> dict[str, object]:
    item_quantities = quantities or ["1"] * len(amounts)
    payload: dict[str, object] = {
        "title": "Trabajo operativo",
        "description": "Descripción comercial",
        "markup_percentage": "50",
        "items": [
            {
                "cost_calculation_id": create_calculation(amount),
                "description": f"Componente {position + 1}",
                "quantity": item_quantities[position],
                "notes": f"Nota {position + 1}",
            }
            for position, amount in enumerate(amounts)
        ],
        "adjustments": [],
    }
    if final_price is not None:
        payload["final_price"] = final_price
    response = client.post("/api/v1/quotes", json=payload)
    assert response.status_code == 201
    result: dict[str, object] = response.json()
    return result


def approve(client: TestClient, quote_id: object) -> None:
    assert client.post(f"/api/v1/quotes/{quote_id}/approve").status_code == 200


def test_one_item_creates_idempotent_order_snapshot_without_stock(
    client: TestClient,
) -> None:
    quote = create_quote(client, ["4000"], final_price="7000")
    approve(client, quote["id"])
    with SessionFactory() as session:
        stock_before = session.scalar(
            select(func.count()).select_from(SupplyStockMovement)
        )

    first = client.post(f"/api/v1/quotes/{quote['id']}/convert")
    second = client.post(f"/api/v1/quotes/{quote['id']}/convert")

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json() == second.json()
    assert first.json()["target_type"] == "order"
    assert re.fullmatch(r"O-\d{4}-\d{6}", first.json()["code"])
    order = client.get(f"/api/v1/orders/{first.json()['target_id']}")
    assert order.status_code == 200
    body = order.json()
    assert body["status"] == "pending"
    assert Decimal(body["technical_total_cost"]) == Decimal("4000")
    assert Decimal(body["quoted_suggested_price"]) == Decimal("6000")
    assert Decimal(body["quoted_final_price"]) == Decimal("7000")

    with SessionFactory() as session:
        item = session.get(QuoteItem, body["source_quote_item_id"])
        assert item is not None
        item.technical_total_cost = Decimal("9999")
        session.commit()
    historical = client.get(f"/api/v1/orders/{body['id']}").json()
    assert Decimal(historical["technical_total_cost"]) == Decimal("4000")

    with SessionFactory() as session:
        assert session.scalar(select(func.count()).select_from(Order)) == 1
        assert session.scalar(select(func.count()).select_from(QuoteConversion)) == 1
        stock_after = session.scalar(
            select(func.count()).select_from(SupplyStockMovement)
        )
    assert stock_before == stock_after


def test_multiple_items_create_project_with_one_component_per_item(
    client: TestClient,
) -> None:
    quote = create_quote(
        client,
        ["1000", "2000", "500"],
        final_price="6000",
    )
    approve(client, quote["id"])

    converted = client.post(f"/api/v1/quotes/{quote['id']}/convert")

    assert converted.status_code == 201
    assert converted.json()["target_type"] == "project"
    assert re.fullmatch(r"P-\d{4}-\d{6}", converted.json()["code"])
    project = client.get(f"/api/v1/projects/{converted.json()['target_id']}").json()
    assert project["status"] == "pending"
    assert Decimal(project["quoted_technical_cost"]) == Decimal("3500")
    assert Decimal(project["quoted_final_price"]) == Decimal("6000")
    assert len(project["components"]) == 3
    assert [
        Decimal(item["technical_total_cost"]) for item in project["components"]
    ] == [
        Decimal("1000"),
        Decimal("2000"),
        Decimal("500"),
    ]
    assert (
        client.post(f"/api/v1/quotes/{quote['id']}/convert").json() == converted.json()
    )


def test_only_approved_quotes_are_convertible(client: TestClient) -> None:
    draft = create_quote(client, ["100"])
    assert client.post(f"/api/v1/quotes/{draft['id']}/convert").status_code == 409
    rejected = client.post(
        f"/api/v1/quotes/{draft['id']}/reject", json={"reason": "No"}
    )
    assert rejected.status_code == 200
    assert client.post(f"/api/v1/quotes/{draft['id']}/convert").status_code == 409
    missing = "00000000-0000-0000-0000-000000000000"
    assert client.post(f"/api/v1/quotes/{missing}/convert").status_code == 404


def test_concurrent_conversion_returns_one_target(client: TestClient) -> None:
    quote = create_quote(client, ["250"])
    approve(client, quote["id"])

    def convert() -> tuple[int, dict[str, object]]:
        with TestClient(app) as concurrent_client:
            response = concurrent_client.post(f"/api/v1/quotes/{quote['id']}/convert")
            return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: convert(), range(2)))

    assert {status for status, _ in results} == {200, 201}
    assert results[0][1] == results[1][1]
    with SessionFactory() as session:
        assert session.scalar(select(func.count()).select_from(Order)) == 1
        assert session.scalar(select(func.count()).select_from(QuoteConversion)) == 1


def test_list_cancel_and_no_direct_creation_or_delete(client: TestClient) -> None:
    quote = create_quote(client, ["100"])
    approve(client, quote["id"])
    converted = client.post(f"/api/v1/quotes/{quote['id']}/convert").json()
    order_id = converted["target_id"]

    assert len(client.get("/api/v1/orders?status=pending").json()) == 1
    cancelled = client.post(f"/api/v1/orders/{order_id}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert client.post(f"/api/v1/orders/{order_id}/cancel").status_code == 409
    assert client.post("/api/v1/orders", json={}).status_code == 405
    assert client.delete(f"/api/v1/orders/{order_id}").status_code == 405
    assert client.post("/api/v1/projects", json={}).status_code == 405


def test_purchase_cost_quote_conversion_preserves_stock(client: TestClient) -> None:
    supply = client.post(
        "/api/v1/supplies",
        json={
            "name": "PLA Hito 7",
            "sku": "PLA-HITO-7",
            "category": "material",
            "base_unit": "g",
        },
    )
    assert supply.status_code == 201
    supply_id = supply.json()["id"]
    purchase = client.post(
        f"/api/v1/supplies/{supply_id}/purchases",
        json={
            "quantity": "1000",
            "total_cost": "18000",
            "currency": "ARS",
            "purchased_at": "2026-09-01T10:00:00Z",
        },
    )
    assert purchase.status_code == 201
    calculation = client.post(
        "/api/v1/cost-calculations",
        json={"supplies": [{"supply_id": supply_id, "quantity": "500", "unit": "g"}]},
    )
    assert calculation.status_code == 201
    quote = client.post(
        "/api/v1/quotes",
        json={
            "title": "Flujo completo",
            "items": [
                {
                    "cost_calculation_id": calculation.json()["id"],
                    "description": "Impresión",
                    "quantity": "1",
                }
            ],
        },
    )
    assert quote.status_code == 201
    approve(client, quote.json()["id"])
    before = client.get(f"/api/v1/supplies/{supply_id}/stock").json()["quantity"]

    converted = client.post(f"/api/v1/quotes/{quote.json()['id']}/convert")

    assert converted.status_code == 201
    assert (
        client.get(f"/api/v1/orders/{converted.json()['target_id']}").status_code == 200
    )
    after = client.get(f"/api/v1/supplies/{supply_id}/stock").json()["quantity"]
    assert Decimal(before) == Decimal("1000")
    assert Decimal(after) == Decimal("1000")
