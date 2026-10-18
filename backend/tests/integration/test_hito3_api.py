from collections.abc import Iterator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.models import SystemSetting
from app.db.session import SessionFactory
from app.main import app
from app.modules.installation.service import INSTALLATION_SETTINGS_KEY
from app.modules.machines.models import Machine

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def clean_hito3_data() -> Iterator[None]:
    with SessionFactory() as session:
        clean(session)
    yield
    with SessionFactory() as session:
        clean(session)


def clean(session: Session) -> None:
    session.execute(delete(Machine))
    session.execute(
        delete(SystemSetting).where(SystemSetting.key == INSTALLATION_SETTINGS_KEY)
    )
    session.commit()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def test_settings_defaults_validation_and_persistence(client: TestClient) -> None:
    defaults = client.get("/api/v1/settings")
    assert defaults.status_code == 200
    assert defaults.json()["currency"] == "ARS"
    assert defaults.json()["deposit_policy"] == "none"

    updated = client.put(
        "/api/v1/settings",
        json={
            "business_name": "Taller API",
            "currency": "USD",
            "country_code": "AR",
            "region": "Chubut",
            "timezone": "America/Argentina/Buenos_Aires",
            "language": "es",
            "deposit_policy": "required",
            "deposit_type": "percentage",
            "deposit_value": "50",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["business_name"] == "Taller API"

    persisted = client.get("/api/v1/settings")
    assert persisted.json()["currency"] == "USD"
    assert persisted.json()["deposit_value"] == "50"

    invalid = client.put(
        "/api/v1/settings",
        json={"timezone": "-03:00", "currency": "ARS", "country_code": "AR"},
    )
    assert invalid.status_code == 422


def test_machine_crud_without_delete_and_with_filters(client: TestClient) -> None:
    created = client.post(
        "/api/v1/machines",
        json={
            "name": "CNC API",
            "machine_type": "cnc",
            "purchase_price": "1250.5000",
        },
    )
    assert created.status_code == 201
    machine_id = created.json()["id"]
    assert Decimal(created.json()["purchase_price"]) == Decimal("1250.5000")
    assert created.json()["currency"] == "ARS"

    fetched = client.get(f"/api/v1/machines/{machine_id}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "CNC API"

    updated = client.patch(
        f"/api/v1/machines/{machine_id}",
        json={"name": "CNC actualizada", "active": False},
    )
    assert updated.status_code == 200
    assert updated.json()["active"] is False

    listed = client.get("/api/v1/machines", params={"active": False})
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [machine_id]

    missing = client.get("/api/v1/machines/00000000-0000-0000-0000-000000000000")
    assert missing.status_code == 404
    assert client.delete(f"/api/v1/machines/{machine_id}").status_code == 405


def test_community_limit_returns_conflict(client: TestClient) -> None:
    for index in range(2):
        response = client.post(
            "/api/v1/machines",
            json={"name": f"Activa {index}", "machine_type": "fdm_printer"},
        )
        assert response.status_code == 201

    rejected = client.post(
        "/api/v1/machines",
        json={"name": "Tercera", "machine_type": "sla_printer"},
    )
    assert rejected.status_code == 409

    invalid = client.post(
        "/api/v1/machines",
        json={"name": "Inválida", "machine_type": "printer"},
    )
    assert invalid.status_code == 422
