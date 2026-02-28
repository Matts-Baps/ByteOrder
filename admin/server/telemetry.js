const { NodeSDK } = require('@opentelemetry/sdk-node')
const { OTLPTraceExporter } = require('@opentelemetry/exporter-trace-otlp-http')
const { HttpInstrumentation } = require('@opentelemetry/instrumentation-http')
const { ExpressInstrumentation } = require('@opentelemetry/instrumentation-express')
const { Resource } = require('@opentelemetry/resources')

const sdk = new NodeSDK({
  resource: new Resource({ 'service.name': process.env.OTEL_SERVICE_NAME || 'byteorder-admin' }),
  traceExporter: new OTLPTraceExporter({ url: process.env.OTEL_ENDPOINT }),
  instrumentations: [new HttpInstrumentation(), new ExpressInstrumentation()],
})

sdk.start()
