// Rate-limiting tests — exercise the express-rate-limit protection on API routes.
// Each test group uses its own isolated app instance so rate-limit counters
// from one describe block don't bleed into another.

const request = require('supertest')

// Use self-hosted auth so we don't need Clerk env vars
process.env.AUTH_MODE = 'self-hosted'
process.env.ADMIN_USERNAME = 'admin'
process.env.ADMIN_PASSWORD = 'testpass'

describe('Rate limiting does not block normal usage', () => {
  let app

  beforeAll(() => {
    jest.resetModules()
    app = require('../server/app')
  })

  it('allows a realistic burst of API requests without rate-limiting', async () => {
    // A kitchen admin panel user loading several pages makes ~30 API requests
    // in quick succession. None of these should be rate-limited.
    for (let i = 0; i < 30; i++) {
      const res = await request(app).get('/api/config')
      expect(res.status).not.toBe(429)
    }
  })
})

describe('Rate limiting blocks excessive traffic', () => {
  let app

  beforeAll(() => {
    jest.resetModules()
    app = require('../server/app')
  })

  it('returns 429 after a sustained flood of API requests', async () => {
    // DoS traffic: hundreds of requests in a single window should be blocked.
    let got429 = false
    for (let i = 0; i < 400; i++) {
      const res = await request(app).get('/api/config')
      if (res.status === 429) {
        got429 = true
        break
      }
    }
    expect(got429).toBe(true)
  })

  it('rate-limit response includes standard RateLimit headers', async () => {
    let res
    for (let i = 0; i < 400; i++) {
      res = await request(app).get('/api/config')
      if (res.status === 429) break
    }
    const hasHeader =
      res.headers['retry-after'] !== undefined ||
      res.headers['ratelimit-limit'] !== undefined ||
      res.headers['x-ratelimit-limit'] !== undefined
    expect(hasHeader).toBe(true)
  })
})
