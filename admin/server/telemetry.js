const { NodeSDK } = require('@opentelemetry/sdk-node')
const { OTLPTraceExporter } = require('@opentelemetry/exporter-trace-otlp-http')
const { OTLPMetricExporter } = require('@opentelemetry/exporter-metrics-otlp-http')
const { PeriodicExportingMetricReader } = require('@opentelemetry/sdk-metrics')
const { HttpInstrumentation } = require('@opentelemetry/instrumentation-http')
const { ExpressInstrumentation } = require('@opentelemetry/instrumentation-express')
const { PgInstrumentation } = require('@opentelemetry/instrumentation-pg')
const { Resource } = require('@opentelemetry/resources')

const endpoint = process.env.OTEL_ENDPOINT

const sdk = new NodeSDK({
  resource: new Resource({ 'service.name': process.env.OTEL_SERVICE_NAME || 'byteorder-admin' }),
  traceExporter: new OTLPTraceExporter({ url: `${endpoint}/v1/traces` }),
  metricReader: new PeriodicExportingMetricReader({
    exporter: new OTLPMetricExporter({ url: `${endpoint}/v1/metrics` }),
  }),
  instrumentations: [
    new HttpInstrumentation(),
    new ExpressInstrumentation(),
    new PgInstrumentation(),
  ],
})

sdk.start()
