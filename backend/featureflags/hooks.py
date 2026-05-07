from __future__ import annotations

from openfeature.hook import Hook
from opentelemetry import trace


class OpenTelemetryFeatureFlagHook(Hook):
    def after(self, hook_context, details, hints) -> None:
        span = trace.get_current_span()
        if span is None or not span.is_recording():
            return

        span.set_attribute("feature_flag.key", hook_context.flag_key)
        span.set_attribute(
            "feature_flag.provider", "django-admin-feature-provider"
        )
        span.set_attribute(
            "feature_flag.reason", str(details.reason or "UNKNOWN")
        )
        span.set_attribute(
            "feature_flag.variant", str(details.variant or details.value)
        )

    def error(self, hook_context, exception, hints) -> None:
        span = trace.get_current_span()
        if span is None or not span.is_recording():
            return
        span.set_attribute("feature_flag.key", hook_context.flag_key)
        span.set_attribute("feature_flag.error", exception.__class__.__name__)
