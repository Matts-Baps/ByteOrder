// OpenTelemetry is configured only from the standard OTEL_* variables (#56).
jest.mock('@opentelemetry/sdk-node', () => {
  const start = jest.fn()
  return { NodeSDK: jest.fn(() => ({ start })), start }
})

const { NodeSDK, start } = require('@opentelemetry/sdk-node')
const { startTelemetry } = require('../server/telemetry')

beforeEach(() => jest.clearAllMocks())

describe('startTelemetry', () => {
  it('does nothing without OTEL_EXPORTER_OTLP_ENDPOINT', () => {
    expect(startTelemetry({})).toBe(false)
    expect(NodeSDK).not.toHaveBeenCalled()
  })

  it('ignores the old OTEL_ENDPOINT variable', () => {
    expect(startTelemetry({ OTEL_ENDPOINT: 'http://collector:4318' })).toBe(false)
    expect(NodeSDK).not.toHaveBeenCalled()
  })

  it('starts the SDK when OTEL_EXPORTER_OTLP_ENDPOINT is set', () => {
    expect(startTelemetry({ OTEL_EXPORTER_OTLP_ENDPOINT: 'http://collector:4318' })).toBe(true)
    expect(NodeSDK).toHaveBeenCalledTimes(1)
    expect(start).toHaveBeenCalledTimes(1)
  })

  it('leaves exporters to the SDK so OTEL_EXPORTER_OTLP_* settings apply', () => {
    startTelemetry({ OTEL_EXPORTER_OTLP_ENDPOINT: 'http://collector:4318' })
    const config = NodeSDK.mock.calls[0][0]
    expect(config.traceExporter).toBeUndefined()
    expect(config.metricReader).toBeUndefined()
    expect(config.metricReaders).toBeUndefined()
    // serviceName would override OTEL_SERVICE_NAME, so only a default resource is set.
    expect(config.serviceName).toBeUndefined()
    expect(config.resource.attributes['service.name']).toBe('byteorder-admin')
  })
})
