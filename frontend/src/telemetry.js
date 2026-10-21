// Browser telemetry with the Dash0 Web SDK (#62). Off unless the container's
// start-up script switched it on in /runtime-config.js.
//
// The SDK sends to /otel on this site. nginx forwards that to the
// OpenTelemetry collector and adds any real credentials, so none are shipped
// to the browser.

// The SDK insists on a token. nginx strips this one before forwarding.
const PLACEHOLDER_TOKEN = 'added-by-nginx'

const INSTRUMENTATIONS = [
  '@dash0/navigation',
  '@dash0/web-vitals',
  '@dash0/error',
  '@dash0/fetch',
  '@dash0/xhr',
  '@dash0/frustration-signals',
]

export async function startTelemetry(
  config = window.__BYTEORDER__?.telemetry,
  origin = window.location.origin,
) {
  if (!config?.enabled) return false

  try {
    // Only download the SDK, and the replay recorder, when they're switched on.
    const { init } = await import('@dash0/sdk-web')
    const opts = {
      serviceName: config.serviceName || 'byteorder-frontend',
      endpoint: { url: `${origin}/otel`, authToken: PLACEHOLDER_TOKEN },
      sessionSamplingRate: config.sampleRate ?? 100,
      enabledInstrumentations: INSTRUMENTATIONS,
    }
    if (config.sessionReplay) {
      const { recorder } = await import('@dash0/sdk-web/session-recording')
      opts.enabledInstrumentations = [...INSTRUMENTATIONS, '@dash0/session-recording']
      // Anything typed (names, chat messages) is replaced with asterisks before
      // it leaves the browser.
      opts.sessionRecording = { recorder, maskAllInputs: true }
    }
    init(opts)
    return true
  } catch (err) {
    // Telemetry must never stop the app from loading.
    console.warn('Browser telemetry failed to start', err)
    return false
  }
}
