// Browser telemetry with the Dash0 Web SDK (#62). Off unless the container's
// start-up script switched it on in /runtime-config.js.
//
// The SDK sends to /otel on this site. nginx forwards that to the
// OpenTelemetry collector and adds any real credentials, so none are shipped
// to the browser.

// The SDK insists on a token. nginx strips this one before forwarding.
const PLACEHOLDER_TOKEN = 'added-by-nginx'

// Everything except session replay, which would record what guests type.
const INSTRUMENTATIONS = [
  '@dash0/navigation',
  '@dash0/web-vitals',
  '@dash0/error',
  '@dash0/fetch',
  '@dash0/xhr',
]

export async function startTelemetry(
  config = window.__BYTEORDER__?.telemetry,
  origin = window.location.origin,
) {
  if (!config?.enabled) return false

  // Only download the SDK when telemetry is on.
  const { init } = await import('@dash0/sdk-web')
  init({
    serviceName: config.serviceName || 'byteorder-frontend',
    endpoint: { url: `${origin}/otel`, authToken: PLACEHOLDER_TOKEN },
    sessionSamplingRate: config.sampleRate ?? 100,
    enabledInstrumentations: INSTRUMENTATIONS,
  })
  return true
}
