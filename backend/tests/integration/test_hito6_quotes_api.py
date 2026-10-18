from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models import SystemSetting
from app.db.session import SessionFactory
from app.main import app
from app.modules.costing.models import CostCalculation, CostCalculationLine
from app.modules.installation.service import INSTALLATION_SETTINGS_KEY
from app.modules.quotes.models import Quote, QuoteAdjustment, QuoteItem
from app.modules.supplies.models import SupplyStockMovement

pytestmark = pytest.mark.integration


def clean(session: Session) -> None:
    session.execute(delete(QuoteAdjustment))
    session.execute(delete(QuoteItem))
    session.execute(delete(Quote))
    session.execute(delete(CostCalculationLine))
    session.execute(delete(CostCalculation))
    session.execute(
        delete(SystemSetting).where(SystemSetting.key == INSTALLATION_SETTINGS_KEY)
    )
    session.commit()


@pytest.fixture(autouse=True)
def clean_quote_data() -> Iterator[None]:
    with SessionFactory() as session:
        clean(session)
    yield
    with SessionFactory() as session:
        clean(session)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def create_calculation(
    amount: str, currency: str = "ARS", *, complete: bool = True, multi: bool = False
) -> str:
    with SessionFactory() as session:
        calculation = CostCalculation(
            calculation_type="technical",
            complete=complete,
            multi_currency=multi,
            warnings=[] if complete else ["Falta costo"],
            calculated_at=datetime.now(UTC),
        )
        calculation.lines = [
            CostCalculationLine(
                position=0,
                category="material",
                description="Snapshot técnico",
                quantity=Decimal("1"),
                unit="unit",
                unit_cost=Decimal(amount) if complete else None,
                currency=currency if complete else None,
                subtotal=Decimal(amount) if complete else None,
                source="test",
                source_reference="test",
                complete=complete,
            )
        ]
        if multi:
            calculation.lines.append(
                CostCalculationLine(
                    position=1,
                    category="extra",
                    description="Otra moneda",
                    quantity=Decimal("1"),
                    unit="item",
                    unit_cost=Decimal("1"),
                    currency="USD",
                    subtotal=Decimal("1"),
                    source="test",
                    source_reference="test",
                    complete=True,
                )
            )
        session.add(calculation)
        session.commit()
        return str(calculation.id)


def quote_payload(calculation_id: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "title": "Presupuesto de prueba",
        "markup_percentage": "50",
        "items": [
            {
                "cost_calculation_id": calculation_id,
                "description": "Trabajo",
                "quantity": "1",
            }
        ],
        "adjustments": [],
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize("currency, expected", [("ARS", "1"), ("USD", "1.2")])
def test_final_rounding_after_all_items_with_deposit(
    client: TestClient, currency: str, expected: str
) -> None:
    settings = client.get("/api/v1/settings").json()
    settings.update(
        deposit_policy="required", deposit_type="percentage", deposit_value="50"
    )
    assert client.put("/api/v1/settings", json=settings).status_code == 200
    calculation_id = create_calculation("0.6000", currency)
    response = client.post(
        "/api/v1/quotes",
        json=quote_payload(
            calculation_id,
            markup_percentage="0",
            items=[
                {
                    "cost_calculation_id": calculation_id,
                    "description": description,
                    "quantity": "1",
                }
                for description in ("A", "B")
            ],
        ),
    )
    assert response.status_code == 201, response.text
    quote = response.json()
    breakdown = quote["breakdown"]
    assert Decimal(breakdown["technical_cost"]) == Decimal("1.2")
    assert Decimal(breakdown["suggested_price"]) == Decimal("1.2")
    assert Decimal(breakdown["final_price"]) == Decimal(expected)
    assert Decimal(breakdown["deposit_amount"]) == Decimal(expected) / 2
    assert quote["final_price_overridden"] is False
    assert all(
        Decimal(item["technical_total_cost"]) == Decimal("0.6")
        for item in quote["items"]
    )
    edited = client.patch(
        f"/api/v1/quotes/{quote['id']}", json={"final_price": "1234.9999"}
    )
    assert edited.status_code == 200, edited.text
    expected_override = "1234" if currency == "ARS" else "1234.9999"
    assert Decimal(edited.json()["breakdown"]["final_price"]) == Decimal(
        expected_override
    )
    assert edited.json()["final_price_overridden"] is True


def test_historical_final_price_survives_reads_text_edits_and_approval(
    client: TestClient,
) -> None:
    calculation_id = create_calculation("1234.87")
    response = client.post(
        "/api/v1/quotes", json=quote_payload(calculation_id, markup_percentage="0")
    )
    assert response.status_code == 201
    quote_id = response.json()["id"]
    # Simula un snapshot anterior a la política, sin reescribir la migración.
    with SessionFactory() as session:
        quote = session.get(Quote, UUID(quote_id))
        assert quote is not None
        quote.final_price = Decimal("1234.87")
        session.commit()
    path = f"/api/v1/quotes/{quote_id}"
    for result in (
        client.get(path),
        client.patch(path, json={"notes": "Texto histórico corregido"}),
        client.post(f"{path}/approve"),
        client.get(path),
    ):
        assert result.status_code == 200, result.text
        assert Decimal(result.json()["breakdown"]["final_price"]) == Decimal("1234.87")


def test_quote_snapshot_update_approval_and_immutability(client: TestClient) -> None:
    calculation_id = create_calculation("1000")
    created = client.post("/api/v1/quotes", json=quote_payload(calculation_id))
    assert created.status_code == 201
    body = created.json()
    assert body["code"].startswith("Q-")
    assert Decimal(body["breakdown"]["technical_cost"]) == Decimal("1000")
    assert Decimal(body["breakdown"]["suggested_price"]) == Decimal("1500")

    settings = client.get("/api/v1/settings").json()
    settings["default_markup_percentage"] = "90"
    assert client.put("/api/v1/settings", json=settings).status_code == 200
    historical = client.get(f"/api/v1/quotes/{body['id']}").json()
    assert Decimal(historical["breakdown"]["suggested_price"]) == Decimal("1500")

    updated = client.patch(
        f"/api/v1/quotes/{body['id']}",
        json={"final_price": "1700", "notes": "Precio acordado"},
    )
    assert updated.status_code == 200
    assert updated.json()["final_price_overridden"] is True
    approved = client.post(f"/api/v1/quotes/{body['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert (
        client.patch(
            f"/api/v1/quotes/{body['id']}", json={"title": "Cambio"}
        ).status_code
        == 409
    )
    assert client.delete(f"/api/v1/quotes/{body['id']}").status_code == 405

    technical = client.get(f"/api/v1/cost-calculations/{calculation_id}").json()
    assert Decimal(technical["totals_by_currency"]["ARS"]) == Decimal("1000")


def test_quantity_multiple_items_adjustments_and_deposit(client: TestClient) -> None:
    settings = client.get("/api/v1/settings").json()
    settings.update(
        {
            "deposit_policy": "required",
            "deposit_type": "percentage",
            "deposit_value": "50",
            "default_markup_percentage": "50",
        }
    )
    assert client.put("/api/v1/settings", json=settings).status_code == 200
    first = create_calculation("1000")
    second = create_calculation("500")
    response = client.post(
        "/api/v1/quotes",
        json={
            "title": "Compuesto",
            "items": [
                {"cost_calculation_id": first, "description": "A", "quantity": "2"},
                {"cost_calculation_id": second, "description": "B", "quantity": "3"},
            ],
            "adjustments": [
                {
                    "description": "Urgencia",
                    "adjustment_type": "surcharge",
                    "value_type": "percentage",
                    "value": "20",
                },
                {
                    "description": "Descuento",
                    "adjustment_type": "discount",
                    "value_type": "fixed",
                    "value": "250",
                },
            ],
        },
    )
    assert response.status_code == 201
    breakdown = response.json()["breakdown"]
    assert Decimal(breakdown["technical_cost"]) == Decimal("3500")
    assert Decimal(breakdown["suggested_price"]) == Decimal("6050")
    assert Decimal(breakdown["deposit_amount"]) == Decimal("3025")


def test_incomplete_and_multi_currency_calculations_are_rejected(
    client: TestClient,
) -> None:
    incomplete = client.post(
        "/api/v1/quotes", json=quote_payload(create_calculation("1", complete=False))
    )
    assert incomplete.status_code == 422
    multi = client.post(
        "/api/v1/quotes", json=quote_payload(create_calculation("1", multi=True))
    )
    assert multi.status_code == 422
    ars = create_calculation("1", "ARS")
    usd = create_calculation("1", "USD")
    combined = client.post(
        "/api/v1/quotes",
        json={
            "title": "Monedas distintas",
            "items": [
                {"cost_calculation_id": ars, "description": "ARS", "quantity": "1"},
                {"cost_calculation_id": usd, "description": "USD", "quantity": "1"},
            ],
        },
    )
    assert combined.status_code == 422


def test_rejection_and_missing_references(client: TestClient) -> None:
    calculation_id = create_calculation("100")
    created = client.post("/api/v1/quotes", json=quote_payload(calculation_id)).json()
    rejected = client.post(
        f"/api/v1/quotes/{created['id']}/reject", json={"reason": "No aceptado"}
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert client.post(f"/api/v1/quotes/{created['id']}/approve").status_code == 409
    missing = "00000000-0000-0000-0000-000000000000"
    assert client.get(f"/api/v1/quotes/{missing}").status_code == 404
    assert client.post("/api/v1/quotes", json=quote_payload(missing)).status_code == 404


def test_quote_does_not_touch_stock(client: TestClient) -> None:
    calculation_id = create_calculation("100")
    with SessionFactory() as session:
        before = session.scalar(select(func.count()).select_from(SupplyStockMovement))
    response = client.post("/api/v1/quotes", json=quote_payload(calculation_id))
    assert response.status_code == 201
    client.post(f"/api/v1/quotes/{response.json()['id']}/approve")
    with SessionFactory() as session:
        after = session.scalar(select(func.count()).select_from(SupplyStockMovement))
    assert before == after


def test_expired_quote_is_terminal_and_null_title_is_invalid(
    client: TestClient,
) -> None:
    calculation_id = create_calculation("100")
    invalid = client.post(
        "/api/v1/quotes",
        json=quote_payload(
            calculation_id,
            valid_until=(date.today() - timedelta(days=1)).isoformat(),
        ),
    )
    assert invalid.status_code == 201
    assert invalid.json()["status"] == "expired"
    assert (
        client.post(f"/api/v1/quotes/{invalid.json()['id']}/approve").status_code == 409
    )

    current = client.post("/api/v1/quotes", json=quote_payload(calculation_id))
    assert (
        client.patch(
            f"/api/v1/quotes/{current.json()['id']}", json={"title": None}
        ).status_code
        == 422
    )
