"""Blobs locales por contenido; no interpreta rutas ni MIME enviados por el cliente."""

import hashlib
import logging
import os
import re
import stat
import struct
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

CHUNK_SIZE = 1024 * 1024
logger = logging.getLogger(__name__)


class StorageError(Exception):
    pass


class UploadTooLargeError(Exception):
    pass


class EmptyFileError(Exception):
    pass


@dataclass(frozen=True)
class StagedFile:
    path: Path
    sha256: str
    size_bytes: int
    detected_mime: str
    technical_metadata: dict[str, str | int]

    @property
    def storage_key(self) -> str:
        return f"sha256/{self.sha256[:2]}/{self.sha256}"


def detect_content(file: BinaryIO, size: int) -> tuple[str, dict[str, str | int]]:
    file.seek(0)
    header = file.read(84)
    if len(header) == 84:
        triangles = struct.unpack("<I", header[80:84])[0]
        if triangles > 0 and size == 84 + 50 * triangles:
            return "model/stl", {"format": "stl_binary", "triangle_count": triangles}
    if (
        header.startswith(b"\x89PNG\r\n\x1a\n")
        and header[12:16] == b"IHDR"
        and len(header) >= 24
    ):
        width, height = struct.unpack(">II", header[16:24])
        return "image/png", {"width": width, "height": height}
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", {}
    if header.startswith(b"%PDF-"):
        return "application/pdf", {}
    # Gramática ASCII acotada por línea; no cargar un STL completo en RAM.
    if header.lstrip().startswith(b"solid"):
        file.seek(0)
        number = rb"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
        vector = number + rb"\s+" + number + rb"\s+" + number
        patterns = [
            rb"facet\s+normal\s+" + vector,
            rb"outer\s+loop",
            *([rb"vertex\s+" + vector] * 3),
            rb"endloop",
            rb"endfacet",
        ]
        first = file.readline(4097).strip()
        valid = (
            len(first) <= 4096 and re.fullmatch(rb"solid(?:\s+.*)?", first) is not None
        )
        index, triangles, ended = 0, 0, False
        while valid:
            line = file.readline(4097)
            if not line:
                break
            if len(line) > 4096:
                valid = False
                break
            line = line.strip()
            if not line:
                continue
            if ended:
                valid = False
                break
            if index == 0 and re.fullmatch(rb"endsolid(?:\s+.*)?", line):
                ended = True
                continue
            if re.fullmatch(patterns[index], line) is None:
                valid = False
                break
            index = (index + 1) % len(patterns)
            if index == 0:
                triangles += 1
        if valid and ended and triangles > 0 and index == 0:
            return "model/stl", {"format": "stl_ascii", "triangle_count": triangles}
    # Lo desconocido se conserva sin inferir tipo por extensión.
    return "application/octet-stream", {}


class LocalAssetStorage:
    def __init__(self, root: Path, max_bytes: int) -> None:
        self.root = root.absolute()
        self.max_bytes = max_bytes

    def directory(self, path: Path) -> None:
        if path.resolve() != path.absolute():
            raise StorageError("El almacenamiento no admite enlaces simbólicos")
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        if path.resolve() != path.absolute():
            raise StorageError("El almacenamiento no admite enlaces simbólicos")

    @contextmanager
    def stage(self, source: BinaryIO) -> Iterator[StagedFile]:
        temporary: Path | None = None
        try:
            self.directory(self.root / "staging")
            with tempfile.NamedTemporaryFile(
                dir=self.root / "staging", delete=False
            ) as target:
                temporary = Path(target.name)
                digest = hashlib.sha256()
                size = 0
                while chunk := source.read(CHUNK_SIZE):
                    size += len(chunk)
                    if size > self.max_bytes:
                        raise UploadTooLargeError
                    digest.update(chunk)
                    target.write(chunk)
                if not size:
                    raise EmptyFileError
                target.flush()
                os.fsync(target.fileno())
            with temporary.open("rb") as content:
                mime, metadata = detect_content(content, size)
            yield StagedFile(temporary, digest.hexdigest(), size, mime, metadata)
        except OSError as error:
            raise StorageError(
                "No se pudo acceder al almacenamiento de recursos"
            ) from error
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    logger.exception("No se pudo limpiar un temporal de recursos")

    def open_verified(self, sha256: str, size: int) -> BinaryIO:
        if re.fullmatch(r"[0-9a-f]{64}", sha256) is None:
            raise StorageError("Identificador de contenido inválido")
        path = self.root / "sha256" / sha256[:2] / sha256
        if path.parent.resolve() != path.parent.absolute():
            raise StorageError("Ruta de almacenamiento inválida")
        try:
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            content = os.fdopen(descriptor, "rb")
            try:
                if not stat.S_ISREG(os.fstat(content.fileno()).st_mode):
                    raise StorageError("El blob no es un archivo regular")
                digest = hashlib.file_digest(content, "sha256").hexdigest()
                if os.fstat(content.fileno()).st_size != size or digest != sha256:
                    raise StorageError("El blob no coincide con su hash o tamaño")
                content.seek(0)
                return content
            except BaseException:
                content.close()
                raise
        except OSError as error:
            raise StorageError("No se pudo leer el contenido del recurso") from error

    def publish(self, staged: StagedFile) -> None:
        path = self.root / staged.storage_key
        try:
            self.directory(path.parent)
            try:
                os.link(staged.path, path)
                for directory in (path.parent, path.parent.parent, self.root):
                    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
                    try:
                        os.fsync(descriptor)
                    finally:
                        os.close(descriptor)
            except FileExistsError:
                pass
            with self.open_verified(staged.sha256, staged.size_bytes):
                pass
        except OSError as error:
            raise StorageError("No se pudo publicar el archivo") from error
