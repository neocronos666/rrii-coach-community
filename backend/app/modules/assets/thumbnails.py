"""Miniaturas raster normalizadas; nunca sirven inline el archivo original."""

from io import BytesIO
from typing import BinaryIO

from PIL import Image, ImageOps

from app.modules.assets.storage import EmptyFileError, UploadTooLargeError

THUMBNAIL_MAX_BYTES = 10 * 1024 * 1024
THUMBNAIL_MAX_PIXELS = 16_000_000
THUMBNAIL_SIZE = 512


class InvalidThumbnailError(Exception):
    pass


def normalize_thumbnail(source: BinaryIO, max_bytes: int) -> BytesIO:
    data = source.read(min(max_bytes, THUMBNAIL_MAX_BYTES) + 1)
    if len(data) > min(max_bytes, THUMBNAIL_MAX_BYTES):
        raise UploadTooLargeError
    if not data:
        raise EmptyFileError
    try:
        with Image.open(BytesIO(data), formats=("PNG", "JPEG")) as candidate:
            if candidate.width * candidate.height > THUMBNAIL_MAX_PIXELS:
                raise InvalidThumbnailError("La imagen supera 16 millones de píxeles")
            if getattr(candidate, "n_frames", 1) != 1:
                raise InvalidThumbnailError("La miniatura debe ser una imagen estática")
            candidate.verify()
        with Image.open(BytesIO(data), formats=("PNG", "JPEG")) as decoded:
            decoded.load()
            decoded.thumbnail(
                (THUMBNAIL_SIZE, THUMBNAIL_SIZE), Image.Resampling.LANCZOS
            )
            with ImageOps.exif_transpose(decoded) as oriented:
                with oriented.convert("RGBA") as normalized:
                    normalized.info.clear()
                    output = BytesIO()
                    normalized.save(output, format="PNG")
        output.seek(0)
        return output
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError) as error:
        raise InvalidThumbnailError(
            "Enviar una imagen PNG o JPEG válida y completa"
        ) from error
