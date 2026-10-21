// OpenTelemetry, configured only through the standard OTEL_* variables.
//
// Export is enabled only when OTEL_EXPORTER_OTLP_ENDPOINT is set. The SDK builds
// the exporters itself, so OTEL_EXPORTER_OTLP_PROTOCOL, _HEADERS, OTEL_SERVICE_NAME
// and OTEL_RESOURCE_ATTRIBUTES all apply.
const DEFAULT_SERVICE_NAME = 'byteorder-admin'

function startTelemetry(env = process.env) {
  if (!env.OTEL_EXPORTER_OTLP_ENDPOINT) return false

  const { NodeSDK } = require('@opentelemetry/sdk-node')
  const { HttpInstrumentation } = require('@opentelemetry/instrumentation-http')
  const { ExpressInstrumentation } = require('@opentelemetry/instrumentation-express')
  const { PgInstrumentation } = require('@opentelemetry/instrumentation-pg')
  const { resourceFromAttributes } = require('@opentelemetry/resources')

  const sdk = new NodeSDK({
    // OTEL_SERVICE_NAME, when set, overrides this default.
    resource: resourceFromAttributes({ 'service.name': DEFAULT_SERVICE_NAME }),
    instrumentations: [
      new HttpInstrumentation(),
      new ExpressInstrumentation(),
      new PgInstrumentation(),
    ],
  })
  sdk.start()
  return true
}

module.exports = { startTelemetry }
