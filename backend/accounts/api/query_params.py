from __future__ import annotations

import re

from django.http import HttpRequest
from ninja.errors import HttpError


def optional_str_query(
    request: HttpRequest,
    name: str,
    *,
    max_length: int,
    pattern: str | None = None,
) -> str | None:
    value = request.GET.get(name)
    if value is None:
        return None

    value = value.strip()
    if not value:
        return None

    if len(value) > max_length:
        raise HttpError(422, f"invalid '{name}' query parameter")
    if pattern and re.fullmatch(pattern, value) is None:
        raise HttpError(422, f"invalid '{name}' query parameter")

    return value
