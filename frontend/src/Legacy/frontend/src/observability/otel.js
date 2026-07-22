import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import { registerInstrumentations } from "@opentelemetry/instrumentation";
import { DocumentLoadInstrumentation } from "@opentelemetry/instrumentation-document-load";
import { FetchInstrumentation } from "@opentelemetry/instrumentation-fetch";
import { XMLHttpRequestInstrumentation } from "@opentelemetry/instrumentation-xml-http-request";
import { resourceFromAttributes } from "@opentelemetry/resources";
import { BatchSpanProcessor } from "@opentelemetry/sdk-trace-base";
import { WebTracerProvider } from "@opentelemetry/sdk-trace-web";

import {
  OTEL_EXPORTER_TRACES_URL,
  OTEL_RUNTIME_SERVICE_NAME,
} from "../services/http/client";

let initialized = false;

export function setupOpenTelemetry() {
  if (initialized || !OTEL_EXPORTER_TRACES_URL) {
    return;
  }

  const provider = new WebTracerProvider({
    resource: resourceFromAttributes({
      "service.name": OTEL_RUNTIME_SERVICE_NAME || "joutak-frontend",
    }),
    spanProcessors: [
      new BatchSpanProcessor(
        new OTLPTraceExporter({
          url: OTEL_EXPORTER_TRACES_URL,
        }),
      ),
    ],
  });

  provider.register();

  registerInstrumentations({
    instrumentations: [
      new DocumentLoadInstrumentation(),
      new FetchInstrumentation({
        semconvStabilityOptIn: "http",
      }),
      new XMLHttpRequestInstrumentation({
        semconvStabilityOptIn: "http",
      }),
    ],
  });

  initialized = true;
}
