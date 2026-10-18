from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db.exceptions import PersistenceError
from app.db.session import SessionFactory
from app.modules.assets.file_models import AssetRevisionFile, FileRole, StoredFile
from app.modules.assets.file_service import AssetFileService
from app.modules.assets.storage import LocalAssetStorage
from tests.integration import test_hito10b_asset_files as files
from tests.test_thumbnails import picture

pytestmark = pytest.mark.integration
client = files.client
storage = files.storage


def test_thumbnail_resize_retry_dedupe_restore_and_inline(client: TestClient) -> None:
    path = files.revisions_path(client)
    revision = path + "/" + files.initial(client, path)
    assert client.get(revision + "/thumbnail").status_code == 404
    payload = picture(format="JPEG")
    first = files.upload(client, revision, payload, "preview.png", "thumbnail")
    assert first["technical_metadata"] == {"width": 512, "height": 256}
    assert first["detected_mime"] == "image/png"
    assert files.upload(client, revision, payload, "preview.png", "thumbnail") == first
    content = client.get(revision + "/thumbnail")
    assert content.status_code == 200
    assert content.headers["content-type"] == "image/png"
    assert content.headers["x-content-type-options"] == "nosniff"
    assert content.headers["content-disposition"].startswith("inline")
    with Image.open(BytesIO(content.content)) as image:
        assert image.size == (512, 256)
    download = client.get(f"{revision}/files/{first['id']}/content")
    assert download.content == content.content
    assert download.headers["content-disposition"].startswith("attachment")
    restored = client.post(revision + "/restore", json={})
    assert restored.status_code == 201
    restored_path = path + "/" + restored.json()["id"]
    assert client.get(restored_path + "/thumbnail").content == content.content
    copied = client.get(restored_path + "/files").json()[0]
    assert copied["id"] != first["id"]
    assert copied["stored_file_id"] == first["stored_file_id"]
    fresh = client.post(path, json={}).json()["id"]
    assert client.get(f"{path}/{fresh}/thumbnail").status_code == 404
    second = files.upload(
        client, f"{path}/{fresh}", payload, "preview.png", "thumbnail"
    )
    assert second["stored_file_id"] == first["stored_file_id"]
    client.delete(path.removesuffix("/revisions"))
    assert client.get(revision + "/thumbnail").content == content.content


def test_invalid_conflicting_and_cross_asset_requests(client: TestClient) -> None:
    path = files.revisions_path(client)
    revision = path + "/" + files.initial(client, path)
    for data, expected in [
        (b"not an image", 422),
        (b"", 422),
        (b"x" * (1024 * 1024 + 1), 413),
    ]:
        response = client.post(
            revision + "/files",
            params={"filename": "preview.png", "role": "thumbnail"},
            content=data,
            headers={"content-type": "application/octet-stream"},
        )
        assert response.status_code == expected, response.text
    assert client.get(revision + "/files").json() == []
    files.upload(client, revision, picture(), "preview.png", "thumbnail")
    response = client.post(
        revision + "/files",
        params={"filename": "other.png", "role": "thumbnail"},
        content=picture((100, 100)),
        headers={"content-type": "application/octet-stream"},
    )
    assert response.status_code == 409
    other_path = files.revisions_path(client)
    assert (
        client.get(
            other_path + "/" + revision.split("/")[-1] + "/thumbnail"
        ).status_code
        == 404
    )
    assert len(client.get(revision + "/files").json()) == 1


def test_concurrent_retries_and_database_uniqueness(
    client: TestClient, storage: LocalAssetStorage
) -> None:
    path = files.revisions_path(client)
    revision_id = UUID(files.initial(client, path))
    asset_id = UUID(path.split("/")[-2])

    def attach(_: int) -> UUID:
        with SessionFactory() as session:
            return (
                AssetFileService(session, storage)
                .attach(
                    asset_id,
                    revision_id,
                    "preview.png",
                    FileRole.THUMBNAIL,
                    BytesIO(picture()),
                )
                .id
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        ids = list(executor.map(attach, range(2)))
    assert ids[0] == ids[1]
    with SessionFactory() as session:
        attachment = session.get(AssetRevisionFile, ids[0])
        assert attachment is not None
        session.add(
            AssetRevisionFile(
                revision_id=revision_id,
                stored_file_id=attachment.stored_file_id,
                filename="other.png",
                role="thumbnail",
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()


def test_thumbnail_rollback_preserves_shared_blob(
    client: TestClient, storage: LocalAssetStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = files.revisions_path(client)
    original_revision = path + "/" + files.initial(client, path)
    original = files.upload(
        client, original_revision, picture(), "preview.png", "thumbnail"
    )
    revision_id = UUID(client.post(path, json={}).json()["id"])
    with SessionFactory() as session:

        def fail() -> None:
            raise SQLAlchemyError("simulated commit failure")

        monkeypatch.setattr(session, "commit", fail)
        with pytest.raises(PersistenceError):
            AssetFileService(session, storage).attach(
                UUID(path.split("/")[-2]),
                revision_id,
                "preview.png",
                FileRole.THUMBNAIL,
                BytesIO(picture()),
            )
        assert len(list(session.scalars(select(StoredFile)))) == 1
        assert len(list(session.scalars(select(AssetRevisionFile)))) == 1
    response = client.get(original_revision + "/thumbnail")
    assert response.status_code == 200
    assert len(response.content) == original["size_bytes"]
    blob = next((storage.root / "sha256").glob("*/*"))
    blob.write_bytes(b"corrupt")
    assert client.get(original_revision + "/thumbnail").status_code == 503


def test_migration_preserves_files_and_guards_thumbnails(client: TestClient) -> None:
    from alembic import command
    from alembic.config import Config

    path = files.revisions_path(client)
    revision = path + "/" + files.initial(client, path)
    original = files.upload(client, revision)
    config = Config("alembic.ini")
    try:
        command.downgrade(config, "20260929_0037")
        command.upgrade(config, "head")
        assert client.get(revision + "/files").json()[0]["id"] == original["id"]
        thumbnail = files.upload(
            client, revision, picture(), "preview.png", "thumbnail"
        )
        with pytest.raises(RuntimeError, match="referencias"):
            command.downgrade(config, "20260929_0037")
        assert client.get(revision + "/thumbnail").status_code == 200
        assert any(
            row["id"] == thumbnail["id"]
            for row in client.get(revision + "/files").json()
        )
    finally:
        command.upgrade(config, "head")


def test_orphan_publication_is_recovered_on_retry(
    client: TestClient, storage: LocalAssetStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = files.revisions_path(client)
    revision = files.initial(client, path)
    with SessionFactory() as session:

        def fail() -> None:
            raise SQLAlchemyError("simulated commit failure")

        monkeypatch.setattr(session, "commit", fail)
        with pytest.raises(PersistenceError):
            AssetFileService(session, storage).attach(
                UUID(path.split("/")[-2]),
                UUID(revision),
                "preview.png",
                FileRole.THUMBNAIL,
                BytesIO(picture()),
            )
        assert session.scalar(select(StoredFile)) is None
        assert session.scalar(select(AssetRevisionFile)) is None
    assert len(list((storage.root / "sha256").glob("*/*"))) == 1
    files.upload(client, path + "/" + revision, picture(), "preview.png", "thumbnail")
    assert len(list((storage.root / "sha256").glob("*/*"))) == 1
    assert client.get(f"{path}/{revision}/thumbnail").status_code == 200
