from __future__ import annotations

import os
from threading import Lock

from django.conf import settings
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_setup_lock = Lock()
_is_setup = False


def _enabled() -> bool:
    return bool(
        os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        or os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
        or os.getenv("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT")
    )


def _response_hook(span, request, response) -> None:
    if span is None or not span.is_recording():
        return
    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        span.set_attribute("enduser.id", str(user.pk))
    span.set_attribute("http.route_hint", request.path)
    span.set_attribute("joutak.component", "django")


def _resource() -> Resource:
    return Resource.create(
        {
            "service.name": getattr(
                settings,
                "OTEL_SERVICE_NAME",
                "joutak-backend",
            )
        }
    )


def setup_observability() -> None:
    global _is_setup

    if not _enabled():
        return

    with _setup_lock:
        if _is_setup:
            return

        resource = _resource()
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(provider)

        metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(),
            export_interval_millis=getattr(
                settings, "OTEL_METRICS_EXPORT_INTERVAL_MS", 60000
            ),
        )
        meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[metric_reader],
        )

        LoggingInstrumentor().instrument(set_logging_format=False)
        DjangoInstrumentor().instrument(response_hook=_response_hook)
        RequestsInstrumentor().instrument()

        set_meter_provider(meter_provider)
        _is_setup = True
