from ninja.errors import HttpError
from ninja import NinjaAPI
from accounts.transport.schemas import ErrorOut
import json


def _normalize_form_errors(raw: str):
    try:
        data = json.loads(raw)
    except Exception:
        return None, None
    if not isinstance(data, dict):
        return None, None

    errors: dict[str, list[dict]] = {}
    fields: dict[str, str] = {}
    for field, entries in data.items():
        if not isinstance(entries, list):
            continue
        norm: list[dict] = []
        for e in entries:
            if isinstance(e, dict):
                msg = (e.get("message") or "").strip() or str(e)
                code = e.get("code")
            else:
                msg = str(e)
                code = None
            norm.append({"message": msg, "code": code})
        if norm:
            errors[field] = norm
            fields[field] = norm[0]["message"]
    return (errors or None), (fields or None)


def install_http_error_handler(api: NinjaAPI) -> None:
    @api.exception_handler(HttpError)
    def on_http_error(request, exc: HttpError):  # noqa: N802
        status = getattr(exc, "status_code", 500)
        raw_detail = getattr(exc, "message", None)
        if raw_detail is None:
            raw_detail = str(exc)
        errors, fields = _normalize_form_errors(str(raw_detail))
        if errors:
            return api.create_response(
                request,
                ErrorOut(
                    detail="validation_error",
                    code=status,
                    errors=errors,
                    fields=fields,
                ),
                status=status,
            )
        return api.create_response(
            request,
            ErrorOut(detail=str(raw_detail), code=status),
            status=status,
        )
