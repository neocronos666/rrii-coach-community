import hashlib
import io
import struct
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.db.exceptions import PersistenceError
from app.db.session import SessionFactory
from app.modules.assets.file_models import AssetRevisionFile, FileRole, StoredFile
from app.modules.assets.file_service import AssetFileService
from app.modules.assets.storage import LocalAssetStorage
from tests.integration import test_hito10b_assets as asset_tests

client = asset_tests.client
create = asset_tests.create

pytestmark = pytest.mark.integration
STL = (
    b"Binary STL".ljust(80, b"\0")
    + struct.pack("<I", 1)
    + struct.pack("<12fH", *([0.0] * 12), 0)
)


@pytest.fixture(autouse=True)
def storage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[LocalAssetStorage]:
    settings = get_settings()
    monkeypatch.setattr(settings, "asset_storage_path", tmp_path / "assets")
    monkeypatch.setattr(settings, "asset_max_upload_bytes", 1024 * 1024)
    yield LocalAssetStorage(
        settings.asset_storage_path, settings.asset_max_upload_bytes
    )


def revisions_path(client: TestClient) -> str:
    asset = create(client)
    return f"/api/v1/assets/{asset['id']}/revisions"


def initial(client: TestClient, path: str) -> str:
    return str(client.get(path).json()[0]["id"])


def upload(
    client: TestClient,
    path: str,
    data: bytes = STL,
    filename: str = "pieza.stl",
    role: str = "manufacturing",
) -> dict[str, object]:
    response = client.post(
        path + "/files",
        params={"filename": filename, "role": role},
        content=data,
        headers={"content-type": "application/octet-stream"},
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


def test_binary_stl_deduplicates_and_downloads_archived_resource(
    client: TestClient, storage: LocalAssetStorage
) -> None:
    paths = [revisions_path(client) for _ in range(2)]
    revisions = [path + "/" + initial(client, path) for path in paths]
    files = [upload(client, path) for path in revisions]
    assert files[0]["id"] != files[1]["id"]
    assert files[0]["stored_file_id"] == files[1]["stored_file_id"]
    assert files[0]["sha256"] == hashlib.sha256(STL).hexdigest()
    assert files[0]["size_bytes"] == len(STL)
    assert files[0]["detected_mime"] == "model/stl"
    assert files[0]["technical_metadata"] == {
        "format": "stl_binary",
        "triangle_count": 1,
    }
    assert "storage_key" not in files[0]
    assert len(list((storage.root / "sha256").glob("*/*"))) == 1
    assert list((storage.root / "staging").iterdir()) == []
    with SessionFactory() as session:
        assert len(list(session.scalars(select(StoredFile)))) == 1
        assert len(list(session.scalars(select(AssetRevisionFile)))) == 2
    client.delete(paths[0].removesuffix("/revisions"))
    download = client.get(f"{revisions[0]}/files/{files[0]['id']}/content")
    assert download.content == STL
    assert download.headers["x-content-type-options"] == "nosniff"
    assert download.headers["content-disposition"].startswith("attachment;")
    assert (
        client.get(f"{revisions[1]}/files/{files[0]['id']}/content").status_code == 404
    )


def test_late_attachment_restore_and_hash_diff(client: TestClient) -> None:
    path = revisions_path(client)
    original = client.get(path).json()[0]
    old_path = path + "/" + original["id"]
    first = upload(client, old_path)
    second = client.post(path, json={"note": "Corrección"}).json()
    new_path = path + "/" + second["id"]
    changed = STL[:-2] + b"\x01\x00"
    upload(client, new_path, changed)
    upload(client, new_path, b"%PDF-1.7\nexample", "manual.pdf", "documentation")
    late = upload(client, old_path, b"CAD source", "fuente.cad", "source")
    assert client.get(old_path).json() == original
    assert str(late["attached_at"]) > original["created_at"]
    restored = client.post(old_path + "/restore", json={}).json()
    restored_files = client.get(f"{path}/{restored['id']}/files").json()
    assert {row["stored_file_id"] for row in restored_files} == {
        first["stored_file_id"],
        late["stored_file_id"],
    }
    assert all(row["id"] not in {first["id"], late["id"]} for row in restored_files)
    assert (
        client.get(old_path + "/files").json()[0]["attached_at"] == late["attached_at"]
    )
    diff = client.get(old_path + "/files-diff/" + second["id"]).json()
    assert [row["filename"] for row in diff["added"]] == ["manual.pdf"]
    assert [row["filename"] for row in diff["removed"]] == ["fuente.cad"]
    assert [row["filename"] for row in diff["content_changed"]] == ["pieza.stl"]
    assert client.get(old_path + "/files-diff/" + restored["id"]).json()[
        "unchanged"
    ] == ["fuente.cad", "pieza.stl"]
    other_path = revisions_path(client)
    assert (
        client.get(old_path + "/files-diff/" + initial(client, other_path)).status_code
        == 404
    )


def test_no_replacement_role_diff_and_untrusted_extension(client: TestClient) -> None:
    path = revisions_path(client)
    old_path = path + "/" + initial(client, path)
    first = upload(client, old_path, b"<script>alert(1)</script>")
    assert first["detected_mime"] == "application/octet-stream"
    duplicate = client.post(
        old_path + "/files",
        params={"filename": "pieza.stl", "role": "source"},
        content=b"other",
        headers={"content-type": "application/octet-stream"},
    )
    assert duplicate.status_code == 409
    second = client.post(path, json={}).json()
    upload(
        client, path + "/" + second["id"], b"<script>alert(1)</script>", role="source"
    )
    diff = client.get(old_path + "/files-diff/" + second["id"]).json()
    assert diff["content_changed"] == []
    assert len(diff["role_changed"]) == 1
    assert client.delete(f"{old_path}/files/{first['id']}").status_code in {404, 405}


@pytest.mark.parametrize(
    "filename",
    ["../x.stl", "/tmp/file", "a\\b", ".", "..", "bad\r\nheader", "\x00", " "],
)
def test_invalid_filename(client: TestClient, filename: str) -> None:
    path = revisions_path(client)
    response = client.post(
        path + "/" + initial(client, path) + "/files",
        params={"filename": filename, "role": "source"},
        content=STL,
        headers={"content-type": "application/octet-stream"},
    )
    assert response.status_code == 422


def test_empty_large_chunked_and_unknown_revision(
    client: TestClient, storage: LocalAssetStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = revisions_path(client)
    url = path + "/" + initial(client, path) + "/files"
    params = {"filename": "x", "role": "source"}
    headers = {"content-type": "application/octet-stream"}
    assert (
        client.post(url, params=params, content=b"", headers=headers).status_code == 422
    )
    monkeypatch.setattr(get_settings(), "asset_max_upload_bytes", 4)
    assert (
        client.post(url, params=params, content=b"12345", headers=headers).status_code
        == 413
    )
    assert (
        client.post(
            url, params=params, content=iter([b"123", b"456"]), headers=headers
        ).status_code
        == 413
    )
    assert (
        client.post(
            url, params=params, content=b"a", headers={"content-type": "text/plain"}
        ).status_code
        == 415
    )
    assert (
        client.post(
            path + f"/{uuid4()}/files", params=params, content=b"1", headers=headers
        ).status_code
        == 404
    )
    assert list((storage.root / "staging").iterdir()) == []
    with SessionFactory() as session:
        assert session.scalar(select(StoredFile)) is None


def test_concurrent_same_blob_single_physical_file(
    client: TestClient, storage: LocalAssetStorage
) -> None:
    paths = [revisions_path(client) for _ in range(3)]
    revision_ids = [UUID(initial(client, path)) for path in paths]
    asset_ids = [UUID(path.split("/")[-2]) for path in paths]
    barrier = Barrier(3)

    def attach(index: int) -> UUID:
        with SessionFactory() as session:
            barrier.wait(timeout=10)
            return (
                AssetFileService(session, storage)
                .attach(
                    asset_ids[index],
                    revision_ids[index],
                    "part.stl",
                    FileRole.MANUFACTURING,
                    io.BytesIO(STL),
                )
                .stored_file_id
            )

    with ThreadPoolExecutor(max_workers=3) as executor:
        assert len(set(executor.map(attach, range(3)))) == 1
    assert len(list((storage.root / "sha256").glob("*/*"))) == 1


def test_commit_failure_keeps_orphan_safe_for_retry(
    client: TestClient, storage: LocalAssetStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = revisions_path(client)
    revision = UUID(initial(client, path))
    asset = UUID(path.split("/")[-2])
    with SessionFactory() as session:

        def fail() -> None:
            raise SQLAlchemyError("simulated commit failure")

        monkeypatch.setattr(session, "commit", fail)
        with pytest.raises(PersistenceError):
            AssetFileService(session, storage).attach(
                asset, revision, "part.stl", FileRole.MANUFACTURING, io.BytesIO(STL)
            )
        assert session.scalar(select(StoredFile)) is None
        assert session.scalar(select(AssetRevisionFile)) is None
    assert len(list((storage.root / "sha256").glob("*/*"))) == 1
    assert list((storage.root / "staging").iterdir()) == []
    upload(client, path + "/" + str(revision))
    assert len(list((storage.root / "sha256").glob("*/*"))) == 1


def test_corrupted_or_missing_blob_never_served(
    client: TestClient, storage: LocalAssetStorage
) -> None:
    path = revisions_path(client)
    revision = path + "/" + initial(client, path)
    attachment = upload(client, revision)
    blob = next((storage.root / "sha256").glob("*/*"))
    blob.write_bytes(b"corrupted")
    assert client.get(f"{revision}/files/{attachment['id']}/content").status_code == 503
    response = client.post(
        revision + "/files",
        params={"filename": "copy.stl", "role": "source"},
        content=STL,
        headers={"content-type": "application/octet-stream"},
    )
    assert response.status_code == 503
    assert len(client.get(revision + "/files").json()) == 1
    blob.unlink()
    assert client.get(f"{revision}/files/{attachment['id']}/content").status_code == 503


def test_failed_reference_does_not_remove_shared_blob(
    client: TestClient, storage: LocalAssetStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = revisions_path(client)
    revision = initial(client, path)
    original = upload(client, path + "/" + revision)
    with SessionFactory() as session:

        def fail() -> None:
            raise SQLAlchemyError("simulated failure")

        monkeypatch.setattr(session, "commit", fail)
        with pytest.raises(PersistenceError):
            AssetFileService(session, storage).attach(
                UUID(path.split("/")[-2]),
                UUID(revision),
                "second.stl",
                FileRole.SOURCE,
                io.BytesIO(STL),
            )
        assert len(list(session.scalars(select(StoredFile)))) == 1
        assert len(list(session.scalars(select(AssetRevisionFile)))) == 1
    assert (
        client.get(f"{path}/{revision}/files/{original['id']}/content").content == STL
    )


def test_disk_failure_rolls_back_references(
    client: TestClient, storage: LocalAssetStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = revisions_path(client)
    revision = path + "/" + initial(client, path)

    def fail(*args: object, **kwargs: object) -> None:
        raise OSError("simulated disk failure")

    with monkeypatch.context() as patch:
        patch.setattr("app.modules.assets.storage.os.link", fail)
        response = client.post(
            revision + "/files",
            params={"filename": "part.stl", "role": "source"},
            content=STL,
            headers={"content-type": "application/octet-stream"},
        )
        assert response.status_code == 503
    with SessionFactory() as session:
        assert session.scalar(select(StoredFile)) is None
        assert session.scalar(select(AssetRevisionFile)) is None
    assert list((storage.root / "staging").iterdir()) == []
    upload(client, revision)
