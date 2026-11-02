import re
from urllib.parse import urlsplit

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import models


class Visibility(models.TextChoices):
    PUBLIC = "public", "Все"
    COMMUNITY = "community", "Сообщество"
    PRIVATE = "private", "Только я"


def validate_safe_url(value):
    if not value:
        return
    URLValidator(schemes=["https"])(value)
    parsed = urlsplit(value)
    if parsed.username or parsed.password or "\\" in value:
        raise ValidationError("Используйте HTTPS URL без пароля.")


def validate_image_reference(value):
    if re.fullmatch(r"/media/hub/[a-f0-9]{32}\.webp", value):
        return
    validate_safe_url(value)
