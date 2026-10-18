import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.api import health as health_module
from app.main import app

client = TestClient(app)
EXPECTED_RESPONSE = {
    "status": "ok",
    "service": "rrii-coach-backend",
}


def test_root_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == EXPECTED_RESPONSE


def test_v1_health() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == EXPECTED_RESPONSE


def test_readiness_when_database_and_schema_are_current(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        health_module,
        "get_database_revisions",
        lambda: ({"20260815_0005"}, {"20260815_0005"}),
    )

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "ok",
        "schema_status": "current",
    }


def test_readiness_when_schema_is_outdated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        health_module,
        "get_database_revisions",
        lambda: ({"20260815_0004"}, {"20260815_0005"}),
    )

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "database": "ok",
        "schema_status": "outdated",
    }


def test_readiness_when_database_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_database_error() -> tuple[set[str], set[str]]:
        raise OperationalError("SELECT 1", {}, Exception("unavailable"))

    monkeypatch.setattr(
        health_module,
        "get_database_revisions",
        raise_database_error,
    )

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "database": "unavailable",
        "schema_status": "unknown",
    }


def test_v1_readiness_uses_same_check(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        health_module,
        "get_database_revisions",
        lambda: ({"20260815_0005"}, {"20260815_0005"}),
    )

    response = client.get("/api/v1/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_cors_preflight_allows_current_api_write_methods() -> None:
    for method, path in (
        ("POST", "/api/v1/quotes"),
        ("PATCH", "/api/v1/quotes/00000000-0000-0000-0000-000000000000"),
        ("PUT", "/api/v1/settings"),
        (
            "DELETE",
            "/api/v1/production-tasks/00000000-0000-0000-0000-000000000000/"
            "dependencies/00000000-0000-0000-0000-000000000000",
        ),
    ):
        response = client.options(
            path,
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": method,
                "Access-Control-Request-Headers": "content-type",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == (
            "http://localhost:3000"
        )
        assert method in response.headers["access-control-allow-methods"]
        assert "Content-Type" in response.headers["access-control-allow-headers"]


def test_cors_rejects_unconfigured_origin() -> None:
    response = client.options(
        "/api/v1/quotes",
        headers={
            "Origin": "https://example.invalid",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
