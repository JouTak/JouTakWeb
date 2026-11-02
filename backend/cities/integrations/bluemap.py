from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

from django.conf import settings

from cities.schemas import LocationIn
from cities.services import fail


def location_from_url(value):
    try:
        parsed = urlsplit(value)
        base = urlsplit(settings.ITMOCRAFT_MAP_BASE_URL)
        parts = parsed.fragment.split(":")
        if (
            parsed.scheme != "https"
            or parsed.netloc != base.netloc
            or parsed.username
            or parsed.password
            or parsed.path not in {"", "/"}
            or parsed.query
            or "\\" in value
            or len(parts) != 10
            or parts[0] not in settings.ITMOCRAFT_MAP_IDS
            or parts[9] not in {"flat", "free", "perspective"}
        ):
            raise ValueError
        numbers = [Decimal(p) for p in parts[1:9]]
        if any(not n.is_finite() or abs(n) > 30_000_000 for n in numbers):
            raise ValueError
        # BlueMap Y is camera state, not the city's terrain height.
        return LocationIn(
            world="overworld",
            map_id=parts[0],
            x=round(numbers[0]),
            z=round(numbers[2]),
            y=None,
        )
    except (ValueError, InvalidOperation):
        fail(
            "CITY_INVALID_MAP_LOCATION",
            "Скопируйте адрес выбранного места из BlueMap сервера.",
            422,
        )


def map_url(city):
    if city.x is None or city.z is None or not city.map_id:
        return None
    if city.map_id not in settings.ITMOCRAFT_MAP_IDS:
        return None
    base = settings.ITMOCRAFT_MAP_BASE_URL.rstrip("/")
    parsed = urlsplit(base)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path
        or parsed.query
        or parsed.fragment
        or "\\" in base
    ):
        return None
    # Observed on the actual deployment; flat-view camera altitude is zero.
    return f"{base}/#{city.map_id}:{city.x}:0:{city.z}:1500:0:0:0:1:flat"
