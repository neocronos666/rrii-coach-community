from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionFactory
from app.main import app
from app.modules.supplies.consumption_models import ProductionRunSupplyConsumption
from tests.integration.conftest import clear_test_database
from tests.integration.test_hito9_reservations import reserve, supply
from tests.integration.test_hito9_runs import new_task, start

pytestmark = pytest.mark.integration


@pytest.fixture
def client() -> Iterator[TestClient]:
    clear_test_database()
    with TestClient(app) as client:
        yield client
    clear_test_database()


def test_consumption_waste_reservation_and_traceability(client: TestClient) -> None:
    material = supply(client)
    task = new_task(client)
    assert (
        client.post(
            f"/api/v1/supplies/{material}/adjustments",
            json={
                "direction": "in",
                "quantity": "1000",
                "reason": "Inicial",
                "occurred_at": "2026-09-01T00:00:00Z",
            },
        ).status_code
        == 201
    )
    reserve(client, task, material, "500")
    run = start(client, task)
    result = {
        "good_quantity": "4",
        "failed_quantity": "6",
        "supply_consumptions": [
            {"supply_id": material, "consumed": "100", "wasted": "15"},
        ],
    }
    response = client.post(f"/api/v1/production-runs/{run}/close", json=result)
    assert response.status_code == 200, response.text
    assert response.json()["warnings"] == []
    availability = client.get(f"/api/v1/supplies/{material}/availability").json()
    assert Decimal(availability["physical_quantity"]) == 900
    assert Decimal(availability["reserved_quantity"]) == 400
    consumption = client.get(
        f"/api/v1/production-runs/{run}/supply-consumptions"
    ).json()[0]
    assert Decimal(consumption["consumed"]) == 100
    assert Decimal(consumption["wasted"]) == 15
    movements = client.get(f"/api/v1/supplies/{material}/movements").json()
    produced = [
        movement for movement in movements if movement["movement_type"] == "consumption"
    ]
    assert len(produced) == 1
    assert Decimal(produced[0]["quantity"]) == -100
    assert produced[0]["run_consumption_id"] == consumption["id"]
    second = start(client, task)
    closed = client.post(
        f"/api/v1/production-runs/{second}/close",
        json={
            "good_quantity": "6",
            "supply_consumptions": [
                {"supply_id": material, "consumed": "372", "wasted": "0"},
            ],
        },
    )
    assert closed.status_code == 200
    availability = client.get(f"/api/v1/supplies/{material}/availability").json()
    assert Decimal(availability["physical_quantity"]) == 528
    assert Decimal(availability["reserved_quantity"]) == 0


def test_missing_stock_warns_and_retry_never_double_consumes(
    client: TestClient,
) -> None:
    material = supply(client)
    task = new_task(client)
    run = start(client, task)
    result = {
        "good_quantity": "1",
        "supply_consumptions": [
            {"supply_id": material, "consumed": "100", "wasted": "15"},
        ],
    }

    def finish(_: int) -> int:
        with TestClient(app) as parallel:
            return parallel.post(
                f"/api/v1/production-runs/{run}/close", json=result
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(finish, [1, 2])) == [200, 200]
    closed = client.get(f"/api/v1/production-runs/{run}").json()
    assert closed["warnings"] == ["insufficient_supply_stock:" + material]
    assert (
        Decimal(client.get(f"/api/v1/supplies/{material}/stock").json()["quantity"])
        == -100
    )
    assert len(client.get(f"/api/v1/supplies/{material}/movements").json()) == 1
    changed = {
        "good_quantity": "1",
        "supply_consumptions": [
            {"supply_id": material, "consumed": "100", "wasted": "20"},
        ],
    }
    assert (
        client.post(f"/api/v1/production-runs/{run}/close", json=changed).status_code
        == 409
    )


def test_invalid_or_missing_supply_rolls_back_entire_close(client: TestClient) -> None:
    material = supply(client)
    task = new_task(client)
    run = start(client, task)
    path = f"/api/v1/production-runs/{run}"
    assert (
        client.post(
            path + "/close",
            json={
                "good_quantity": "10",
                "supply_consumptions": [
                    {"supply_id": material, "consumed": "10", "wasted": "11"},
                ],
            },
        ).status_code
        == 422
    )
    line = {"supply_id": material, "consumed": "10"}
    assert (
        client.post(
            path + "/close",
            json={"good_quantity": "10", "supply_consumptions": [line, line]},
        ).status_code
        == 422
    )
    missing = {"supply_id": str(uuid4()), "consumed": "10"}
    assert (
        client.post(
            path + "/close",
            json={"good_quantity": "10", "supply_consumptions": [line, missing]},
        ).status_code
        == 404
    )
    assert client.get(path).json()["status"] == "running"
    assert client.get(path + "/supply-consumptions").json() == []
    assert client.get(f"/api/v1/supplies/{material}/movements").json() == []
    assert (
        client.get(f"/api/v1/production-tasks/{task}").json()["status"] == "in_progress"
    )


def test_database_rejects_waste_above_consumption(client: TestClient) -> None:
    material = supply(client)
    run = start(client, new_task(client))
    with SessionFactory() as session:
        session.add(
            ProductionRunSupplyConsumption(
                run_id=UUID(run),
                supply_id=UUID(material),
                consumed=Decimal("10"),
                wasted=Decimal("11"),
                unit="g",
            )
        )
        with pytest.raises(IntegrityError) as error:
            session.commit()
        assert "wasted_subset" in str(error.value.orig)
        session.rollback()
