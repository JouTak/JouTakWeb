"""Public, re-encoded images in the project's existing Django media storage."""

from io import BytesIO
from uuid import uuid4

from accounts.api.errors import raise_structured_error
from decouple import config
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from ninja import Schema
from PIL import Image, ImageOps, UnidentifiedImageError

from backend.ratelimiting import ratelimit_method


class ImageOut(Schema):
    url: str


def upload_image(request, actor, upload):
    if ratelimit_method(
        request,
        group="hub.images",
        rate=config("RATELIMIT_HUB_IMAGES", default="20/h"),
        key=lambda _group, _request: f"user:{actor.pk}",
    ):
        raise_structured_error(
            429,
            detail="Лимит загрузок исчерпан. Попробуйте позже.",
            error_code="IMAGE_RATE_LIMITED",
        )
    return store_image(upload)


def store_image(upload):
    def invalid():
        raise_structured_error(
            422,
            detail="Выберите PNG, JPEG или WebP до 3 МБ и 16 мегапикселей.",
            error_code="IMAGE_INVALID",
        )

    if upload.size > 3 * 1024 * 1024 or upload.content_type not in {
        "image/png",
        "image/jpeg",
        "image/webp",
    }:
        invalid()
    try:
        raw = upload.read(3 * 1024 * 1024 + 1)
        if len(raw) > 3 * 1024 * 1024:
            invalid()
        with Image.open(BytesIO(raw)) as source:
            if (
                source.format not in {"PNG", "JPEG", "WEBP"}
                or source.width * source.height > 16_000_000
            ):
                invalid()
            source.load()
            picture = ImageOps.exif_transpose(source).convert("RGBA")
            picture.thumbnail((2400, 2400))
            output = BytesIO()
            picture.save(output, format="WEBP", quality=85, exif=b"")
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
    ):
        invalid()
    name = default_storage.save(
        f"hub/{uuid4().hex}.webp", ContentFile(output.getvalue())
    )
    return ImageOut(url=f"/media/{name}")
