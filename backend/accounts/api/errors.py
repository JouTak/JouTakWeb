from __future__ import annotations

from typing import Any, Never

from ninja.errors import HttpError


class StructuredHttpError(HttpError):
    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        super().__init__(status_code, payload)
        self.payload = payload


def raise_structured_error(
    status_code: int,
    *,
    detail: str,
    error_code: str | None = None,
    blocking_reasons: list[str] | None = None,
) -> Never:
    payload: dict[str, Any] = {"detail": detail}
    if error_code:
        payload["error_code"] = error_code
    if blocking_reasons is not None:
        payload["blocking_reasons"] = blocking_reasons
    raise StructuredHttpError(status_code, payload)


def raise_field_error(
    field: str,
    message: str,
    code: str = "invalid",
) -> Never:
    # 422 Unprocessable Entity mirrors how ninja/pydantic signal
    # schema-level validation failures. Keep field-level business
    # rule violations on the same status code so callers have a single
    # predicate (`status === 422` → render per-field errors); plain
    # 400 stays reserved for non-field domain failures
    # (`{"detail": "..."}`).
    raise StructuredHttpError(
        422,
        {field: [{"message": message, "code": code}]},
    )
