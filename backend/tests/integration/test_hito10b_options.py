from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db.exceptions import PersistenceError
from app.db.session import SessionFactory
from app.main import app
from app.modules.options.exceptions import OptionConflictError
from app.modules.options.models import OptionDefinition, OptionValue
from app.modules.options.schemas import OptionDefinitionCreate, OptionValueCreate
from app.modules.options.service import OptionService
from tests.integration.conftest import clear_test_database

pytestmark = pytest.mark.integration
ROOT = "/api/v1/option-definitions"


@pytest.fixture
def client() -> Iterator[TestClient]:
    clear_test_database()
    with TestClient(app) as client:
        yield client
    clear_test_database()


def definition(client: TestClient, name: str = "Sombrero") -> str:
    response = client.post(ROOT, json={"name": name})
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def test_semantic_value_without_family_or_file(client: TestClient) -> None:
    definition_id = definition(client, "  Terminación  ")
    assert UUID(definition_id).version == 4
    record = client.get(f"{ROOT}/{definition_id}").json()
    assert record["name"] == "Terminación"
    assert record["created_at"].endswith(("Z", "+00:00"))
    response = client.post(f"{ROOT}/{definition_id}/values", json={"name": "Mate"})
    assert response.status_code == 201
    value = response.json()
    assert UUID(value["id"]).version == 4
    assert value["definition_id"] == definition_id
    assert value["family_id"] is None
    assert value["active"] is True
    assert client.get(f"{ROOT}/{definition_id}/values/{value['id']}").json() == value
    for field in ("asset_id", "stored_file_id", "definition_id"):
        assert (
            client.post(
                f"{ROOT}/{definition_id}/values",
                json={"name": "Inválida", field: str(uuid4())},
            ).status_code
            == 422
        )


def test_family_links_design_not_adaptation(client: TestClient) -> None:
    family = client.post("/api/v1/asset-families", json={"name": "Gaucho"}).json()
    for name in ("Gaucho Pikachu", "Gaucho Raichu"):
        assert (
            client.post(
                "/api/v1/assets", json={"name": name, "family_id": family["id"]}
            ).status_code
            == 201
        )
    definition_id = definition(client)
    value = client.post(
        f"{ROOT}/{definition_id}/values",
        json={"name": "Gaucho", "family_id": family["id"]},
    )
    assert value.status_code == 201
    assert value.json()["family_id"] == family["id"]
    path = f"{ROOT}/{definition_id}/values/{value.json()['id']}"
    assert client.patch(path, json={"family_id": None}).json()["family_id"] is None
    assert client.patch(path, json={"family_id": family["id"]}).status_code == 200
    assert client.patch(path, json={"asset_id": str(uuid4())}).status_code == 422
    assert len(client.get("/api/v1/assets").json()) == 2


def test_names_unique_within_definition_and_parent_scoping(client: TestClient) -> None:
    first, second = definition(client), definition(client, "Acabado")
    assert client.post(ROOT, json={"name": " Sombrero "}).status_code == 409
    first_value = client.post(f"{ROOT}/{first}/values", json={"name": "Normal"}).json()
    assert (
        client.post(f"{ROOT}/{first}/values", json={"name": " Normal "}).status_code
        == 409
    )
    assert (
        client.post(f"{ROOT}/{second}/values", json={"name": "Normal"}).status_code
        == 201
    )
    wrong = f"{ROOT}/{second}/values/{first_value['id']}"
    assert client.get(wrong).status_code == 404
    assert client.patch(wrong, json={"name": "No cambiar"}).status_code == 404
    right = f"{ROOT}/{first}/values/{first_value['id']}"
    assert client.get(right).json()["name"] == "Normal"
    assert client.patch(right, json={"definition_id": second}).status_code == 422
    another = client.post(f"{ROOT}/{first}/values", json={"name": "Otro"}).json()
    assert client.patch(right, json={"name": another["name"]}).status_code == 409
    assert client.get(right).json()["name"] == "Normal"


def test_inactive_metadata_preserves_identity_and_values(client: TestClient) -> None:
    definition_id = definition(client)
    path = f"{ROOT}/{definition_id}"
    value = client.post(path + "/values", json={"name": "Gaucho"}).json()
    value_path = path + f"/values/{value['id']}"
    response = client.patch(
        value_path,
        json={
            "name": "Gaucho clásico",
            "description": "Diseño reutilizable",
            "active": False,
        },
    )
    assert response.status_code == 200
    assert response.json()["id"] == value["id"]
    assert response.json()["created_at"] == value["created_at"]
    assert client.get(path + "/values", params={"active": True}).json() == []
    assert len(client.get(path + "/values", params={"active": False}).json()) == 1
    assert (
        client.patch(
            path, json={"active": False, "description": "Temporal"}
        ).status_code
        == 200
    )
    assert client.get(ROOT, params={"active": True}).json() == []
    assert len(client.get(ROOT, params={"active": False}).json()) == 1
    assert client.get(value_path).status_code == 200
    assert client.delete(value_path).status_code == 405
    assert client.delete(path).status_code == 405
    assert (
        client.patch(path, json={"active": True, "description": None}).json()[
            "description"
        ]
        is None
    )
    assert (
        client.patch(value_path, json={"active": True, "description": None}).status_code
        == 200
    )


def test_search_pagination_and_missing_parent(client: TestClient) -> None:
    first = definition(client, "A% especial")
    definition(client, "B normal")
    assert len(client.get(ROOT, params={"search": "%"}).json()) == 1
    assert (
        client.get(ROOT, params={"offset": 1, "limit": 1}).json()[0]["name"]
        == "B normal"
    )
    for name in ("A_única", "B", "C"):
        assert (
            client.post(f"{ROOT}/{first}/values", json={"name": name}).status_code
            == 201
        )
    assert len(client.get(f"{ROOT}/{first}/values", params={"search": "_"}).json()) == 1
    assert (
        client.get(f"{ROOT}/{first}/values", params={"offset": 1, "limit": 1}).json()[
            0
        ]["name"]
        == "B"
    )
    for suffix in ("", "/values", f"/values/{uuid4()}"):
        assert client.get(f"{ROOT}/{uuid4()}{suffix}").status_code == 404
    assert (
        client.post(f"{ROOT}/{uuid4()}/values", json={"name": "No existe"}).status_code
        == 404
    )
    for params in ({"limit": 101}, {"limit": 0}, {"offset": -1}):
        assert client.get(ROOT, params=params).status_code == 422
        assert client.get(f"{ROOT}/{first}/values", params=params).status_code == 422


@pytest.mark.parametrize("payload", [{"name": " "}, {"name": None}, {"active": None}])
def test_invalid_metadata(client: TestClient, payload: dict[str, object]) -> None:
    definition_id = definition(client)
    path = f"{ROOT}/{definition_id}"
    value = client.post(path + "/values", json={"name": "Gaucho"}).json()
    assert client.patch(path, json=payload).status_code == 422
    assert (
        client.patch(path + f"/values/{value['id']}", json=payload).status_code == 422
    )
    assert client.post(ROOT, json={"name": "Nueva", **payload}).status_code == 422
    assert (
        client.post(path + "/values", json={"name": "Nueva", **payload}).status_code
        == 422
    )


def test_missing_family_rolls_back_creation_and_update(client: TestClient) -> None:
    definition_id = definition(client)
    path = f"{ROOT}/{definition_id}/values"
    assert (
        client.post(
            path, json={"name": "No persistir", "family_id": str(uuid4())}
        ).status_code
        == 404
    )
    assert client.get(path).json() == []
    value = client.post(path, json={"name": "Original"}).json()
    assert (
        client.patch(
            path + f"/{value['id']}",
            json={"name": "No cambiar", "family_id": str(uuid4())},
        ).status_code
        == 404
    )
    assert client.get(path).json()[0]["name"] == "Original"
    with SessionFactory() as session:
        session.add(
            OptionValue(definition_id=UUID(definition_id), name="FK", family_id=uuid4())
        )
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()


def test_concurrent_duplicate_definitions_have_one_identity(client: TestClient) -> None:
    def register(_: int) -> bool:
        with SessionFactory() as session:
            try:
                OptionService(session).create_definition(
                    OptionDefinitionCreate(name="Compartida")
                )
                return True
            except OptionConflictError:
                return False

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(register, range(2))) == [False, True]
    assert len(client.get(ROOT).json()) == 1


def test_commit_failure_rolls_back_value(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    definition_id = UUID(definition(client))
    with SessionFactory() as session:

        def fail_commit() -> None:
            session.flush()
            raise SQLAlchemyError("Fallo simulado después del flush")

        monkeypatch.setattr(session, "commit", fail_commit)
        with pytest.raises(PersistenceError):
            OptionService(session).create_value(
                definition_id, OptionValueCreate(name="No parcial")
            )
        assert session.scalar(select(OptionValue)) is None
        assert session.get(OptionDefinition, definition_id) is not None
