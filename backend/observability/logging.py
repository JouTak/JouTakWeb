from __future__ import annotations

import logging
from contextvars import ContextVar, Token

from opentelemetry import trace

_request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
_request_host_var: ContextVar[str] = ContextVar("request_host", default="-")
_request_path_var: ContextVar[str] = ContextVar("request_path", default="-")


def set_request_log_context(
    *,
    request_id: str,
    request_host: str,
    request_path: str,
) -> tuple[Token[str], Token[str], Token[str]]:
    return (
        _request_id_var.set(request_id),
        _request_host_var.set(request_host),
        _request_path_var.set(request_path),
    )


def clear_request_log_context(
    tokens: tuple[Token[str], Token[str], Token[str]],
) -> None:
    request_id_token, request_host_token, request_path_token = tokens
    _request_id_var.reset(request_id_token)
    _request_host_var.reset(request_host_token)
    _request_path_var.reset(request_path_token)


class RequestLogContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        span_context = trace.get_current_span().get_span_context()
        record.request_id = _request_id_var.get()
        record.request_host = _request_host_var.get()
        record.request_path = _request_path_var.get()
        record.trace_id = (
            f"{span_context.trace_id:032x}"
            if span_context and span_context.is_valid
            else "-"
        )
        record.span_id = (
            f"{span_context.span_id:016x}"
            if span_context and span_context.is_valid
            else "-"
        )
        return True


def build_logging_config(*, root_level: str) -> dict[str, object]:
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_context": {
                "()": "observability.logging.RequestLogContextFilter"
            }
        },
        "formatters": {
            "structured": {
                "format": (
                    "%(asctime)s %(levelname)s %(name)s "
                    "[request_id=%(request_id)s trace_id=%(trace_id)s "
                    "span_id=%(span_id)s host=%(request_host)s "
                    "path=%(request_path)s] "
                    "%(message)s"
                )
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "filters": ["request_context"],
                "formatter": "structured",
            }
        },
        "root": {"handlers": ["console"], "level": root_level},
    }
