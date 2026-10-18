from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.db.exceptions import PersistenceError
from app.db.session import SessionFactory
from app.modules.recipes.service_catalog import ServiceCatalog
from app.modules.recipes.service_models import ServiceDefinition
from app.modules.recipes.service_schemas import ServiceDefinitionCreate
from tests.integration import test_hito10b_options as catalog_tests

pytestmark = pytest.mark.integration
client = catalog_tests.client
ROOT = "/api/v1/service-definitions"


def test_service_metadata_and_multiple_contexts_without_mutation(
    client: TestClient,
) -> None:
    response = client.post(
        ROOT,
        json={
            "name": " Lijado ",
            "instructions": "Usar lija fina.",
            "action_template": "Lijar {piece}",
        },
    )
    assert response.status_code == 201
    service = response.json()
    assert service["name"] == "Lijado"
    assert UUID(service["id"]).version == 4
    assert service["created_at"].endswith(("Z", "+00:00"))
    path = f"{ROOT}/{service['id']}"
    for piece in ("brazo derecho de Hulk", "cabello de Goku"):
        result = client.post(
            path + "/action-preview", json={"values": {"piece": piece}}
        )
        assert result.status_code == 200
        assert result.json()["action"] == "Lijar " + piece
        assert result.json()["instructions"] == "Usar lija fina."
    assert client.get(path).json() == service
    assert len(client.get(ROOT).json()) == 1
    assert client.post(path + "/action-preview", json={}).status_code == 409
    assert client.patch(path, json={"active": False}).status_code == 200
    assert client.get(ROOT, params={"active": True}).json() == []
    assert len(client.get(ROOT, params={"active": False}).json()) == 1
    # El preview administrativo sigue disponible al editar un servicio inactivo.
    assert (
        client.post(
            path + "/action-preview", json={"values": {"piece": "pieza"}}
        ).status_code
        == 200
    )
    updated = client.patch(
        path, json={"active": True, "action_template": None, "instructions": None}
    )
    assert updated.status_code == 200
    assert updated.json()["created_at"] == service["created_at"]
    assert client.post(path + "/action-preview", json={}).json()["action"] == "Lijado"
    assert client.delete(path).status_code == 405


def test_services_search_duplicates_and_missing(client: TestClient) -> None:
    first = client.post(ROOT, json={"name": "A% especial"}).json()
    assert client.post(ROOT, json={"name": "B"}).status_code == 201
    assert client.post(ROOT, json={"name": " A% especial "}).status_code == 409
    path = f"{ROOT}/{first['id']}"
    assert client.patch(path, json={"name": "B"}).status_code == 409
    assert client.get(path).json()["name"] == "A% especial"
    assert len(client.get(ROOT, params={"search": "%"}).json()) == 1
    assert client.get(ROOT, params={"offset": 1, "limit": 1}).json()[0]["name"] == "B"
    for params in ({"offset": -1}, {"limit": 0}, {"limit": 101}):
        assert client.get(ROOT, params=params).status_code == 422
    assert client.get(f"{ROOT}/{uuid4()}").status_code == 404
    assert client.patch(f"{ROOT}/{uuid4()}", json={"name": "X"}).status_code == 404
    assert client.post(f"{ROOT}/{uuid4()}/action-preview", json={}).status_code == 404


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", " "),
        ("name", None),
        ("active", None),
        ("action_template", "{piece.__class__}"),
        ("action_template", "{piece!r}"),
        ("action_template", " "),
        ("duration_minutes", 10),
        ("hourly_rate", "10"),
    ],
)
def test_invalid_service_payload(client: TestClient, field: str, value: object) -> None:
    service = client.post(ROOT, json={"name": "Válido"}).json()
    assert client.post(ROOT, json={"name": "Nuevo", field: value}).status_code == 422
    assert (
        client.patch(f"{ROOT}/{service['id']}", json={field: value}).status_code == 422
    )
    assert client.get(f"{ROOT}/{service['id']}").json() == service


def test_preview_context_is_bounded_text_not_business_quantity(
    client: TestClient,
) -> None:
    service = client.post(
        ROOT,
        json={
            "name": "Preparar",
            "action_template": "Preparar {quantity} de {product}",
        },
    ).json()
    path = f"{ROOT}/{service['id']}/action-preview"
    assert (
        client.post(
            path, json={"values": {"quantity": "2,5", "product": "Figura"}}
        ).json()["action"]
        == "Preparar 2,5 de Figura"
    )
    for values in (
        {"unknown": "x"},
        {"piece": "x" * 1001},
        {"quantity": 2.5},
        {"piece": ""},
    ):
        assert client.post(path, json={"values": values}).status_code == 422


def test_service_commit_failure_rolls_back(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    with SessionFactory() as session:

        def fail_commit() -> None:
            session.flush()
            raise SQLAlchemyError("Fallo simulado")

        monkeypatch.setattr(session, "commit", fail_commit)
        with pytest.raises(PersistenceError):
            ServiceCatalog(session).create(ServiceDefinitionCreate(name="No parcial"))
        assert session.scalar(select(ServiceDefinition)) is None
