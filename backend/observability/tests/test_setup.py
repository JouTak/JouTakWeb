from __future__ import annotations

from unittest.mock import Mock, patch

from django.test import SimpleTestCase

import observability.setup as observability_setup


class ObservabilitySetupTests(SimpleTestCase):
    def test_setup_runs_only_once(self):
        resource = Mock(name="resource")
        tracer_provider = Mock(name="tracer_provider")
        meter_provider = Mock(name="meter_provider")

        with (
            patch("observability.setup._enabled", return_value=True),
            patch("observability.setup._resource", return_value=resource),
            patch("observability.setup.OTLPSpanExporter"),
            patch("observability.setup.BatchSpanProcessor"),
            patch("observability.setup.OTLPMetricExporter"),
            patch("observability.setup.PeriodicExportingMetricReader"),
            patch(
                "observability.setup.TracerProvider",
                return_value=tracer_provider,
            ) as tracer_provider_factory,
            patch(
                "observability.setup.MeterProvider",
                return_value=meter_provider,
            ) as meter_provider_factory,
            patch(
                "observability.setup.set_meter_provider"
            ) as set_meter_provider,
            patch("observability.setup.trace") as trace_module,
            patch(
                "observability.setup.LoggingInstrumentor"
            ) as logging_instrumentor,
            patch(
                "observability.setup.DjangoInstrumentor"
            ) as django_instrumentor,
            patch(
                "observability.setup.RequestsInstrumentor"
            ) as requests_instrumentor,
        ):
            observability_setup._is_setup = False

            observability_setup.setup_observability()
            observability_setup.setup_observability()

        self.assertTrue(observability_setup._is_setup)
        self.assertEqual(tracer_provider_factory.call_count, 1)
        self.assertEqual(meter_provider_factory.call_count, 1)
        self.assertEqual(trace_module.set_tracer_provider.call_count, 1)
        self.assertEqual(set_meter_provider.call_count, 1)
        self.assertEqual(
            logging_instrumentor.return_value.instrument.call_count,
            1,
        )
        self.assertEqual(
            django_instrumentor.return_value.instrument.call_count,
            1,
        )
        self.assertEqual(
            requests_instrumentor.return_value.instrument.call_count,
            1,
        )
        self.assertEqual(tracer_provider.add_span_processor.call_count, 1)
