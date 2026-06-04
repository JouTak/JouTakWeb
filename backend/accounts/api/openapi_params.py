from __future__ import annotations

from accounts.transport.schemas import (
    NEXT_PATH_MAX_LENGTH,
    PROVIDER_ID_MAX_LENGTH,
    PROVIDER_ID_MIN_LENGTH,
    PROVIDER_ID_PATTERN,
    REVOKE_REASON_MAX_LENGTH,
    REVOKE_REASON_PATTERN,
    SESSION_ID_MAX_LENGTH,
)

SESSION_ID_OPENAPI_PARAMETER = {
    "in": "path",
    "name": "sid",
    "schema": {
        "type": "string",
        "minLength": 1,
        "maxLength": SESSION_ID_MAX_LENGTH,
        "title": "Sid",
    },
    "required": True,
}
REVOKE_REASON_OPENAPI_PARAMETER = {
    "in": "query",
    "name": "reason",
    "schema": {
        "type": "string",
        "minLength": 1,
        "maxLength": REVOKE_REASON_MAX_LENGTH,
        "pattern": REVOKE_REASON_PATTERN,
        "title": "Reason",
    },
    "required": False,
}
PROVIDER_OPENAPI_PARAMETER = {
    "in": "path",
    "name": "provider",
    "schema": {
        "type": "string",
        "minLength": PROVIDER_ID_MIN_LENGTH,
        "maxLength": PROVIDER_ID_MAX_LENGTH,
        "pattern": PROVIDER_ID_PATTERN,
        "title": "Provider",
    },
    "required": True,
}
NEXT_OPENAPI_PARAMETER = {
    "in": "query",
    "name": "next",
    "schema": {
        "type": "string",
        "maxLength": NEXT_PATH_MAX_LENGTH,
        "title": "Next",
    },
    "required": False,
}
