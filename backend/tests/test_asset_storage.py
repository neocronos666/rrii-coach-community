import io
import struct
from pathlib import Path

import pytest

from app.modules.assets.storage import (
    EmptyFileError,
    LocalAssetStorage,
    StorageError,
    UploadTooLargeError,
    detect_content,
)

ASCII_STL = b"""solid triangle
facet normal 0 0 1
outer loop
vertex 0 0 0
vertex 1 0 0
vertex 0 1 0
endloop
endfacet
endsolid triangle
"""


def test_ascii_stl_and_malformed_content() -> None:
    assert detect_content(io.BytesIO(ASCII_STL), len(ASCII_STL)) == (
        "model/stl",
        {"format": "stl_ascii", "triangle_count": 1},
    )
    for data in [
        b"solid not an STL",
        ASCII_STL.replace(b"vertex", b"wrong"),
        ASCII_STL + b"unexpected",
    ]:
        assert (
            detect_content(io.BytesIO(data), len(data))[0] == "application/octet-stream"
        )


def test_minimal_signatures_and_technical_metadata() -> None:
    png = (
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", 13)
        + b"IHDR"
        + struct.pack(">II", 32, 64)
    )
    assert detect_content(io.BytesIO(png), len(png)) == (
        "image/png",
        {"width": 32, "height": 64},
    )
    for data, mime in [
        (b"%PDF-1.7", "application/pdf"),
        (b"\xff\xd8\xff\xe0", "image/jpeg"),
        (b"custom CAD", "application/octet-stream"),
    ]:
        assert detect_content(io.BytesIO(data), len(data))[0] == mime


def test_stage_limits_cleanup_and_publish_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = LocalAssetStorage(tmp_path / "assets", 3)
    for data, error in [(b"", EmptyFileError), (b"1234", UploadTooLargeError)]:
        with pytest.raises(error), storage.stage(io.BytesIO(data)):
            pytest.fail("No debe publicar contenido inválido")
        assert list((storage.root / "staging").iterdir()) == []

    def failure(*args: object, **kwargs: object) -> None:
        raise OSError("disk failure")

    monkeypatch.setattr("app.modules.assets.storage.os.link", failure)
    with pytest.raises(StorageError), storage.stage(io.BytesIO(b"123")) as staged:
        storage.publish(staged)
    assert list((storage.root / "staging").iterdir()) == []


def test_symlink_rejected_without_writing_outside_root(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "assets"
    root.symlink_to(outside, target_is_directory=True)
    with (
        pytest.raises(StorageError),
        LocalAssetStorage(root, 100).stage(io.BytesIO(b"abc")),
    ):
        pytest.fail("No debe aceptar symlinks")
    assert list(outside.iterdir()) == []


def test_blob_symlink_is_not_followed(tmp_path: Path) -> None:
    storage = LocalAssetStorage(tmp_path / "assets", 100)
    with storage.stage(io.BytesIO(b"abc")) as staged:
        storage.publish(staged)
        path = storage.root / staged.storage_key
        path.unlink()
        outside = tmp_path / "outside"
        outside.write_bytes(b"abc")
        path.symlink_to(outside)
        with pytest.raises(StorageError):
            storage.open_verified(staged.sha256, staged.size_bytes)
