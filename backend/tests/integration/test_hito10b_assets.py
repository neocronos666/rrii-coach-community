from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db.exceptions import PersistenceError
from app.db.session import SessionFactory
from app.main import app
from app.modules.assets.file_models import AssetRevisionFile, StoredFile
from app.modules.assets.models import (
    UNCATEGORIZED_ID,
    Asset,
    AssetCategory,
    AssetRevision,
)
from app.modules.assets.schemas import AssetCreate, RevisionCreate
from app.modules.assets.service import AssetService
from app.modules.assets.structure_models import (
    AssetCompatibility,
    AssetCompositionComponent,
    AssetFamily,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client
    with SessionFactory() as session:
        session.execute(update(Asset).values(current_revision_id=None))
        session.execute(update(AssetRevision).values(restored_from_revision_id=None))
        session.execute(delete(AssetRevisionFile))
        session.execute(delete(StoredFile))
        session.execute(delete(AssetCompositionComponent))
        session.execute(delete(AssetCompatibility))
        session.execute(delete(AssetRevision))
        session.execute(delete(Asset))
        session.execute(delete(AssetFamily))
        session.execute(
            delete(AssetCategory).where(AssetCategory.id != UNCATEGORIZED_ID)
        )
        session.commit()


def create(client: TestClient, **fields: object) -> dict[str, object]:
    response = client.post("/api/v1/assets", json={"name": "Recurso sin STL", **fields})
    assert response.status_code == 201, response.text
    return dict(response.json())


def test_logical_assets_duplicate_names_code_archive_and_metadata(
    client: TestClient,
) -> None:
    first = create(
        client,
        third_party=True,
        author="Autor",
        origin="Biblioteca externa",
        license="CC-BY",
        source_url="https://example.org/model",
        usage_notes="Atribuir autor",
    )
    second = create(client)
    assert first["name"] == second["name"]
    assert first["code"] != second["code"]
    assert str(first["code"]).startswith("AST-")
    assert UUID(str(first["id"])).version == 4
    assert first["author"] == "Autor"
    assert first["license"] == "CC-BY"
    assert first["usage_notes"] == "Atribuir autor"
    assert first["category_id"] == str(UNCATEGORIZED_ID)
    path = f"/api/v1/assets/{first['id']}"
    original = client.get(path + "/revisions").json()[0]
    assert original["number"] == 1
    assert original["created_at"].endswith("Z") or original["created_at"].endswith(
        "+00:00"
    )
    assert client.patch(path, json={"code": "CUSTOM"}).status_code == 422
    assert (
        client.patch(
            path, json={"current_revision_id": second["current_revision_id"]}
        ).status_code
        == 422
    )
    assert client.delete(path).json()["archived"] is True
    assert client.delete(path).status_code == 200
    assert len(client.get("/api/v1/assets").json()) == 1
    assert (
        client.get("/api/v1/assets", params={"archived": True}).json()[0]["id"]
        == first["id"]
    )
    assert client.get(path + "/revisions").json() == [original]
    assert (
        client.patch(path, json={"archived": False, "name": "Actualizado"}).status_code
        == 200
    )
    assert client.get(path).json()["code"] == first["code"]
    assert (
        len(client.get("/api/v1/assets", params={"search": str(first["code"])}).json())
        == 1
    )
    assert (
        len(client.get("/api/v1/assets", params={"limit": 1, "offset": 1}).json()) == 1
    )


def test_category_delete_reassigns_active_and_archived_without_history_loss(
    client: TestClient,
) -> None:
    response = client.post("/api/v1/asset-categories", json={"name": "Imágenes"})
    assert response.status_code == 201
    category = response.json()["id"]
    first = create(client, category_id=category)
    second = create(client, category_id=category)
    client.delete(f"/api/v1/assets/{second['id']}")
    assert (
        client.patch(
            f"/api/v1/asset-categories/{category}", json={"name": "Fotos"}
        ).status_code
        == 200
    )
    assert client.delete(f"/api/v1/asset-categories/{category}").status_code == 204
    for asset in [first, second]:
        current = client.get(f"/api/v1/assets/{asset['id']}").json()
        assert current["category_id"] == str(UNCATEGORIZED_ID)
        assert current["current_revision_id"] == asset["current_revision_id"]
    assert (
        client.delete(f"/api/v1/asset-categories/{UNCATEGORIZED_ID}").status_code == 409
    )
    assert (
        client.patch(
            f"/api/v1/asset-categories/{UNCATEGORIZED_ID}", json={"name": "Otro"}
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/v1/asset-categories", json={"name": "Uncategorized"}
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/v1/assets", json={"name": "No persistir", "category_id": category}
        ).status_code
        == 404
    )
    with SessionFactory() as session:
        assert len(list(session.scalars(select(Asset)))) == 2


def test_revision_restore_is_new_preserves_old_and_scopes_identity(
    client: TestClient,
) -> None:
    first = create(client, revision_note="Original")
    second = create(client)
    path = f"/api/v1/assets/{first['id']}"
    original = client.get(path + "/revisions").json()[0]
    new = client.post(path + "/revisions", json={"note": "Corrección"})
    assert new.status_code == 201
    assert new.json()["number"] == 2
    restored = client.post(path + f"/revisions/{original['id']}/restore", json={})
    assert restored.status_code == 201
    assert restored.json()["number"] == 3
    assert restored.json()["id"] != original["id"]
    assert restored.json()["restored_from_revision_id"] == original["id"]
    assert restored.json()["note"] == "Original"
    assert client.get(path).json()["current_revision_id"] == restored.json()["id"]
    assert client.get(path + f"/revisions/{original['id']}").json() == original
    assert (
        client.post(
            path + f"/revisions/{second['current_revision_id']}/restore", json={}
        ).status_code
        == 404
    )
    assert len(client.get(path + "/revisions").json()) == 3
    assert (
        client.patch(
            path + f"/revisions/{original['id']}", json={"note": "Reescritura"}
        ).status_code
        == 405
    )
    with SessionFactory() as session:
        asset = session.get(Asset, UUID(str(first["id"])))
        assert asset is not None
        asset.current_revision_id = UUID(str(second["current_revision_id"]))
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()


def test_concurrent_revisions_serialize_number_and_current(client: TestClient) -> None:
    asset_id = UUID(str(create(client)["id"]))

    def publish(number: int) -> int:
        with SessionFactory() as session:
            revision = AssetService(session).create_revision(
                asset_id, RevisionCreate(note=str(number))
            )
            return revision.number

    with ThreadPoolExecutor(max_workers=3) as executor:
        assert sorted(executor.map(publish, range(3))) == [2, 3, 4]
    current = client.get(f"/api/v1/assets/{asset_id}").json()
    assert (
        client.get(
            f"/api/v1/assets/{asset_id}/revisions/{current['current_revision_id']}"
        ).json()["number"]
        == 4
    )


def test_initial_revision_failure_rolls_back_asset(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    with SessionFactory() as session:
        service = AssetService(session)
        original_add = service.repository.add

        def fail_revision(entity: Asset | AssetCategory | AssetRevision) -> None:
            if isinstance(entity, AssetRevision):
                raise SQLAlchemyError("Fallo simulado de persistencia")
            original_add(entity)

        monkeypatch.setattr(service.repository, "add", fail_revision)
        with pytest.raises(PersistenceError):
            service.create(AssetCreate(name="No debe quedar parcial"))
        assert session.scalar(select(Asset)) is None
    assert client.get("/api/v1/assets").json() == []


@pytest.mark.parametrize(
    "payload",
    [
        {"name": " "},
        {"name": "A", "code": "X"},
        {"name": "A", "source_url": "file:///etc/passwd"},
        {"name": "A", "third_party": None},
    ],
)
def test_invalid_asset_input(client: TestClient, payload: dict[str, object]) -> None:
    assert client.post("/api/v1/assets", json=payload).status_code == 422


def test_missing_and_null_updates(client: TestClient) -> None:
    assert client.get(f"/api/v1/assets/{uuid4()}").status_code == 404
    path = f"/api/v1/assets/{create(client)['id']}"
    for field in ["name", "category_id", "third_party", "archived"]:
        assert client.patch(path, json={field: None}).status_code == 422
    assert (
        client.patch(path, json={"description": None, "author": None}).status_code
        == 200
    )
