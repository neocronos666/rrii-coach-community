from io import BytesIO

import pytest
from PIL import Image

from app.modules.assets.storage import EmptyFileError, UploadTooLargeError
from app.modules.assets.thumbnails import InvalidThumbnailError, normalize_thumbnail


def picture(size: tuple[int, int] = (1200, 600), *, format: str = "PNG") -> bytes:
    output = BytesIO()
    with Image.new("RGB", size, (10, 20, 30)) as image:
        image.save(output, format=format)
    return output.getvalue()


@pytest.mark.parametrize("format", ["PNG", "JPEG"])
def test_resize_proportion_and_strip_metadata(format: str) -> None:
    result = normalize_thumbnail(BytesIO(picture(format=format)), 10_000_000)
    with Image.open(result) as image:
        assert image.format == "PNG"
        assert image.size == (512, 256)
        assert image.mode == "RGBA"
        assert image.info == {}


def test_orientation_and_no_upscaling() -> None:
    source = BytesIO()
    with Image.new("RGB", (100, 50)) as image:
        exif = image.getexif()
        exif[274] = 6
        exif[315] = "Private author"
        image.save(source, format="JPEG", exif=exif)
    source.seek(0)
    with Image.open(normalize_thumbnail(source, 10_000_000)) as result:
        assert result.size == (50, 100)
        assert not result.getexif()
        assert result.info == {}


@pytest.mark.parametrize(
    "data", [b"<svg></svg>", b"%PDF-1.0", b"\x89PNG\r\n\x1a\n", picture()[:100]]
)
def test_reject_invalid_images(data: bytes) -> None:
    with pytest.raises(InvalidThumbnailError):
        normalize_thumbnail(BytesIO(data), 10_000_000)


def test_limits_and_animation() -> None:
    with pytest.raises(EmptyFileError):
        normalize_thumbnail(BytesIO(), 10)
    with pytest.raises(UploadTooLargeError):
        normalize_thumbnail(BytesIO(b"x" * 11), 10)
    with pytest.raises(InvalidThumbnailError, match="píxeles"):
        normalize_thumbnail(BytesIO(picture((4001, 4000))), 10_000_000)
    output = BytesIO()
    with (
        Image.new("RGBA", (5, 5), "red") as first,
        Image.new("RGBA", (5, 5), "blue") as second,
    ):
        first.save(output, format="PNG", save_all=True, append_images=[second])
    output.seek(0)
    with pytest.raises(InvalidThumbnailError, match="estática"):
        normalize_thumbnail(output, 10_000_000)


def test_transparency_is_preserved() -> None:
    source = BytesIO()
    with Image.new("RGBA", (4, 4), (10, 20, 30, 50)) as image:
        image.save(source, format="PNG")
    source.seek(0)
    with Image.open(normalize_thumbnail(source, 100_000)) as result:
        assert result.size == (4, 4)
        assert result.getpixel((0, 0)) == (10, 20, 30, 50)
