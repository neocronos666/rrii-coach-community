from collections.abc import Iterator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.session import SessionFactory
from app.main import app
from app.modules.supplies.models import (
    Supply,
    SupplyPresentation,
    SupplyPurchase,
    SupplyStockMovement,
)

pytestmark = pytest.mark.integration


def clean(session: Session) -> None:
    session.execute(delete(SupplyStockMovement))
    session.execute(delete(SupplyPurchase))
    session.execute(delete(SupplyPresentation))
    session.execute(delete(Supply))
    session.commit()


@pytest.fixture(autouse=True)
def clean_hito4_data() -> Iterator[None]:
    with SessionFactory() as session:
        clean(session)
    yield
    with SessionFactory() as session:
        clean(session)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def create_supply(client: TestClient, *, sku: str = "PLA-NEG-001") -> str:
    response = client.post(
        "/api/v1/supplies",
        json={
            "name": "PLA Negro",
            "sku": sku,
            "category": "material",
            "base_unit": "g",
        },
    )
    assert response.status_code == 201
    return str(response.json()["id"])


def test_supply_crud_filters_and_unique_sku(client: TestClient) -> None:
    supply_id = create_supply(client)
    fetched = client.get(f"/api/v1/supplies/{supply_id}")
    assert fetched.status_code == 200
    updated = client.patch(
        f"/api/v1/supplies/{supply_id}", json={"brand": "Printalot", "active": False}
    )
    assert updated.status_code == 200
    assert updated.json()["active"] is False
    listed = client.get(
        "/api/v1/supplies", params={"active": False, "category": "material"}
    )
    assert [item["id"] for item in listed.json()] == [supply_id]
    duplicate = client.post(
        "/api/v1/supplies",
        json={
            "name": "Otro",
            "sku": "PLA-NEG-001",
            "category": "other",
            "base_unit": "unit",
        },
    )
    assert duplicate.status_code == 409
    assert client.delete(f"/api/v1/supplies/{supply_id}").status_code == 405


def test_purchase_stock_movement_cost_and_unit_lock(client: TestClient) -> None:
    supply_id = create_supply(client)
    presentation = client.post(
        f"/api/v1/supplies/{supply_id}/presentations",
        json={"name": "Rollo 1 kg", "quantity": "1", "unit": "kg"},
    )
    assert presentation.status_code == 201
    purchase = client.post(
        f"/api/v1/supplies/{supply_id}/purchases",
        json={
            "quantity": "2",
            "presentation_id": presentation.json()["id"],
            "total_cost": "36000",
            "currency": "ARS",
            "purchased_at": "2026-08-15T12:00:00Z",
        },
    )
    assert purchase.status_code == 201
    assert Decimal(purchase.json()["quantity"]) == Decimal("2000")
    stock = client.get(f"/api/v1/supplies/{supply_id}/stock")
    assert Decimal(stock.json()["quantity"]) == Decimal("2000")
    movements = client.get(f"/api/v1/supplies/{supply_id}/movements")
    assert movements.json()[0]["movement_type"] == "purchase"
    cost = client.get(f"/api/v1/supplies/{supply_id}/estimated-cost")
    assert Decimal(cost.json()["unit_cost"]) == Decimal("18")
    assert cost.json()["currency"] == "ARS"
    second_purchase = client.post(
        f"/api/v1/supplies/{supply_id}/purchases",
        json={
            "quantity": "1000",
            "total_cost": "20",
            "currency": "USD",
            "purchased_at": "2026-08-15T13:00:00Z",
        },
    )
    assert second_purchase.status_code == 201
    latest_cost = client.get(f"/api/v1/supplies/{supply_id}/estimated-cost")
    assert Decimal(latest_cost.json()["unit_cost"]) == Decimal("0.02")
    assert latest_cost.json()["currency"] == "USD"
    assert (
        client.patch(
            f"/api/v1/supplies/{supply_id}", json={"base_unit": "kg"}
        ).status_code
        == 409
    )
    assert len(client.get(f"/api/v1/supplies/{supply_id}/purchases").json()) == 2


def test_adjustments_and_failed_outgoing_are_atomic(client: TestClient) -> None:
    supply_id = create_supply(client, sku="ARG-001")
    incoming = client.post(
        f"/api/v1/supplies/{supply_id}/adjustments",
        json={
            "direction": "in",
            "quantity": "1000",
            "reason": "Stock inicial",
            "occurred_at": "2026-08-15T12:00:00Z",
        },
    )
    assert incoming.status_code == 201
    outgoing = client.post(
        f"/api/v1/supplies/{supply_id}/adjustments",
        json={
            "direction": "out",
            "quantity": "100",
            "reason": "Corrección",
            "occurred_at": "2026-08-15T13:00:00Z",
        },
    )
    assert outgoing.status_code == 201
    second_incoming = client.post(
        f"/api/v1/supplies/{supply_id}/adjustments",
        json={
            "direction": "in",
            "quantity": "50",
            "reason": "Reconteo",
            "occurred_at": "2026-08-15T13:30:00Z",
        },
    )
    assert second_incoming.status_code == 201
    rejected = client.post(
        f"/api/v1/supplies/{supply_id}/adjustments",
        json={
            "direction": "out",
            "quantity": "951",
            "reason": "Exceso",
            "occurred_at": "2026-08-15T14:00:00Z",
        },
    )
    assert rejected.status_code == 409
    stock = client.get(f"/api/v1/supplies/{supply_id}/stock")
    assert Decimal(stock.json()["quantity"]) == Decimal("950")
    assert len(client.get(f"/api/v1/supplies/{supply_id}/movements").json()) == 3


def test_validation_not_found_and_cost_unavailable(client: TestClient) -> None:
    missing = "00000000-0000-0000-0000-000000000000"
    assert client.get(f"/api/v1/supplies/{missing}").status_code == 404
    invalid = client.post(
        "/api/v1/supplies",
        json={"name": "Inválido", "category": "material", "base_unit": "ton"},
    )
    assert invalid.status_code == 422
    supply_id = create_supply(client, sku="SIN-COSTO")
    assert client.get(f"/api/v1/supplies/{supply_id}/estimated-cost").status_code == 404
