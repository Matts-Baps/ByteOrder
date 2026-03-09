import { WebTracerProvider } from '@opentelemetry/sdk-trace-web'
import { BatchSpanProcessor, StackContextManager } from '@opentelemetry/sdk-trace-web'
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http'
import { Resource } from '@opentelemetry/resources'
import { W3CTraceContextPropagator } from '@opentelemetry/core'
import { registerInstrumentations } from '@opentelemetry/instrumentation'
import { DocumentLoadInstrumentation } from '@opentelemetry/instrumentation-document-load'
import { FetchInstrumentation } from '@opentelemetry/instrumentation-fetch'
import { XMLHttpRequestInstrumentation } from '@opentelemetry/instrumentation-xml-http-request'

const endpoint = import.meta.env.VITE_OTEL_ENDPOINT

if (endpoint) {
  const provider = new WebTracerProvider({
    resource: new Resource({ 'service.name': 'byteorder-frontend' }),
  })

  provider.addSpanProcessor(
    new BatchSpanProcessor(
      new OTLPTraceExporter({ url: `${endpoint}/v1/traces` }),
    ),
  )

  provider.register({
    contextManager: new StackContextManager(),
    propagator: new W3CTraceContextPropagator(),
  })

  // Propagate trace context to all outbound requests so the full
  // Frontend → Admin → Menu/Order service chain is linked.
  registerInstrumentations({
    instrumentations: [
      new DocumentLoadInstrumentation(),
      new FetchInstrumentation({
        propagateTraceHeaderCorsUrls: /.*/,
      }),
      new XMLHttpRequestInstrumentation({
        propagateTraceHeaderCorsUrls: /.*/,
      }),
    ],
  })
}
