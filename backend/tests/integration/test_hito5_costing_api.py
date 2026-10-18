from collections.abc import Iterator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.models import SystemSetting
from app.db.session import SessionFactory
from app.main import app
from app.modules.costing.models import CostCalculation, CostCalculationLine
from app.modules.installation.service import INSTALLATION_SETTINGS_KEY
from app.modules.machines.models import Machine
from app.modules.supplies.models import (
    Supply,
    SupplyPresentation,
    SupplyPurchase,
    SupplyStockMovement,
)

pytestmark = pytest.mark.integration


def clean(session: Session) -> None:
    session.execute(delete(CostCalculationLine))
    session.execute(delete(CostCalculation))
    session.execute(delete(SupplyStockMovement))
    session.execute(delete(SupplyPurchase))
    session.execute(delete(SupplyPresentation))
    session.execute(delete(Supply))
    session.execute(delete(Machine))
    session.execute(
        delete(SystemSetting).where(SystemSetting.key == INSTALLATION_SETTINGS_KEY)
    )
    session.commit()


@pytest.fixture(autouse=True)
def clean_costing_data() -> Iterator[None]:
    with SessionFactory() as session:
        clean(session)
    yield
    with SessionFactory() as session:
        clean(session)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def configure_rates(client: TestClient) -> None:
    response = client.put(
        "/api/v1/settings",
        json={
            "business_name": None,
            "currency": "ARS",
            "country_code": "AR",
            "region": None,
            "timezone": "America/Argentina/Buenos_Aires",
            "language": "es",
            "deposit_policy": "none",
            "deposit_type": None,
            "deposit_value": None,
            "electricity_price_per_kwh": "180",
            "design_hour_rate": None,
            "preproduction_hour_rate": None,
            "postproduction_hour_rate": "6000",
            "assembly_hour_rate": None,
            "support_hour_rate": None,
            "training_hour_rate": None,
            "pretransport_hour_rate": None,
        },
    )
    assert response.status_code == 200


def create_supply_with_purchase(client: TestClient) -> str:
    supply = client.post(
        "/api/v1/supplies",
        json={
            "name": "PLA Negro",
            "sku": "PLA-COST",
            "category": "material",
            "base_unit": "g",
        },
    )
    supply_id = str(supply.json()["id"])
    purchase = client.post(
        f"/api/v1/supplies/{supply_id}/purchases",
        json={
            "quantity": "1000",
            "total_cost": "18000",
            "currency": "ARS",
            "purchased_at": "2026-08-15T10:00:00Z",
        },
    )
    assert purchase.status_code == 201
    return supply_id


def create_machine(client: TestClient) -> str:
    response = client.post(
        "/api/v1/machines",
        json={
            "name": "Ender Costos",
            "machine_type": "fdm_printer",
            "purchase_price": "500000",
            "currency": "ARS",
            "rated_power_w": "350",
            "useful_life_hours": "10000",
        },
    )
    assert response.status_code == 201
    return str(response.json()["id"])


def test_combined_cost_snapshot_and_no_stock_consumption(client: TestClient) -> None:
    configure_rates(client)
    supply_id = create_supply_with_purchase(client)
    machine_id = create_machine(client)
    created = client.post(
        "/api/v1/cost-calculations",
        json={
            "machine_id": machine_id,
            "machine_duration_minutes": 120,
            "supplies": [{"supply_id": supply_id, "quantity": "0.5", "unit": "kg"}],
            "labor": [{"labor_type": "postproduction", "duration_minutes": 30}],
            "extras": [
                {"description": "Extra manual", "amount": "100", "currency": "ARS"}
            ],
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["complete"] is True
    assert body["multi_currency"] is False
    assert Decimal(body["totals_by_currency"]["ARS"]) == Decimal("12326")
    material = next(line for line in body["lines"] if line["category"] == "material")
    assert Decimal(material["quantity"]) == Decimal("500")
    assert Decimal(material["unit_cost"]) == Decimal("18")
    assert Decimal(material["subtotal"]) == Decimal("9000")

    stock = client.get(f"/api/v1/supplies/{supply_id}/stock")
    assert Decimal(stock.json()["quantity"]) == Decimal("1000")

    client.post(
        f"/api/v1/supplies/{supply_id}/purchases",
        json={
            "quantity": "1000",
            "total_cost": "30000",
            "currency": "ARS",
            "purchased_at": "2026-08-15T11:00:00Z",
        },
    )
    historical = client.get(f"/api/v1/cost-calculations/{body['id']}")
    assert historical.status_code == 200
    old_material = next(
        line for line in historical.json()["lines"] if line["category"] == "material"
    )
    assert Decimal(old_material["unit_cost"]) == Decimal("18")
    assert Decimal(old_material["subtotal"]) == Decimal("9000")
    assert client.patch(f"/api/v1/cost-calculations/{body['id']}").status_code == 405
    assert client.delete(f"/api/v1/cost-calculations/{body['id']}").status_code == 405


def test_insufficient_stock_warns_but_calculates(client: TestClient) -> None:
    supply_id = create_supply_with_purchase(client)
    response = client.post(
        "/api/v1/cost-calculations",
        json={"supplies": [{"supply_id": supply_id, "quantity": "1500", "unit": "g"}]},
    )
    assert response.status_code == 201
    assert response.json()["complete"] is True
    assert any("Stock insuficiente" in item for item in response.json()["warnings"])
    stock = client.get(f"/api/v1/supplies/{supply_id}/stock")
    assert Decimal(stock.json()["quantity"]) == Decimal("1000")


def test_missing_sources_are_successful_incomplete_lines(client: TestClient) -> None:
    configure_rates(client)
    supply = client.post(
        "/api/v1/supplies",
        json={
            "name": "Sin costo",
            "category": "component",
            "base_unit": "unit",
        },
    )
    response = client.post(
        "/api/v1/cost-calculations",
        json={
            "supplies": [
                {"supply_id": supply.json()["id"], "quantity": "1", "unit": "unit"}
            ],
            "labor": [{"labor_type": "design", "duration_minutes": 30}],
        },
    )
    assert response.status_code == 201
    assert response.json()["complete"] is False
    assert len(response.json()["warnings"]) == 2
    assert all(line["subtotal"] is None for line in response.json()["lines"])


def test_costing_api_validates_references_and_request(client: TestClient) -> None:
    missing = "00000000-0000-0000-0000-000000000000"
    not_found = client.post(
        "/api/v1/cost-calculations",
        json={"supplies": [{"supply_id": missing, "quantity": "1", "unit": "g"}]},
    )
    assert not_found.status_code == 404
    invalid = client.post(
        "/api/v1/cost-calculations",
        json={"machine_duration_minutes": 30},
    )
    assert invalid.status_code == 422
    assert client.get(f"/api/v1/cost-calculations/{missing}").status_code == 404
