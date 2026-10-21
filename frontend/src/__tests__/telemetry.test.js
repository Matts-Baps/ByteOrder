import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@dash0/sdk-web', () => ({ init: vi.fn() }))
vi.mock('@dash0/sdk-web/session-recording', () => ({ recorder: 'rrweb-recorder' }))

import { init } from '@dash0/sdk-web'
import { startTelemetry } from '../telemetry'

const ORIGIN = 'https://byteorder.example'

describe('browser telemetry', () => {
  beforeEach(() => vi.clearAllMocks())

  it('stays off without runtime config', async () => {
    expect(await startTelemetry(undefined, ORIGIN)).toBe(false)
    expect(init).not.toHaveBeenCalled()
  })

  it('stays off when the runtime config says so', async () => {
    expect(await startTelemetry({ enabled: false }, ORIGIN)).toBe(false)
    expect(init).not.toHaveBeenCalled()
  })

  it('sends to nginx on the same site, which adds any real credentials', async () => {
    expect(await startTelemetry({ enabled: true, serviceName: 'byteorder-frontend', sampleRate: 25 }, ORIGIN)).toBe(true)
    const opts = init.mock.calls[0][0]
    expect(opts.endpoint.url).toBe(`${ORIGIN}/otel`)
    // The SDK requires a token; nginx strips it before forwarding.
    expect(opts.endpoint.authToken).toBeTruthy()
    expect(opts.serviceName).toBe('byteorder-frontend')
    expect(opts.sessionSamplingRate).toBe(25)
  })

  it('does not record sessions for replay unless asked to', async () => {
    await startTelemetry({ enabled: true }, ORIGIN)
    const opts = init.mock.calls[0][0]
    expect(opts.enabledInstrumentations).toBeDefined()
    expect(opts.enabledInstrumentations).not.toContain('@dash0/session-recording')
    expect(opts.sessionRecording).toBeUndefined()
  })

  it('records sessions for replay when asked to, with typed text masked', async () => {
    await startTelemetry({ enabled: true, sessionReplay: true }, ORIGIN)
    const opts = init.mock.calls[0][0]
    expect(opts.enabledInstrumentations).toContain('@dash0/session-recording')
    expect(opts.sessionRecording.recorder).toBe('rrweb-recorder')
    expect(opts.sessionRecording.maskAllInputs).toBe(true)
  })

  it('falls back to sensible defaults', async () => {
    await startTelemetry({ enabled: true }, ORIGIN)
    const opts = init.mock.calls[0][0]
    expect(opts.serviceName).toBe('byteorder-frontend')
    expect(opts.sessionSamplingRate).toBe(100)
  })
})
