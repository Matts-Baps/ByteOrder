// Rate-limiting tests — exercise the express-rate-limit protection on API routes.
// Each test group uses its own isolated app instance so rate-limit counters
// from one describe block don't bleed into another.

const request = require('supertest')

// Use self-hosted auth so we don't need Clerk env vars
process.env.AUTH_MODE = 'self-hosted'
process.env.ADMIN_USERNAME = 'admin'
process.env.ADMIN_PASSWORD = 'testpass'

describe('Rate limiting is applied to API routes', () => {
  let app

  beforeAll(() => {
    // Clear module cache so each test suite gets a fresh rate-limit state
    jest.resetModules()
    app = require('../server/app')
  })

  it('returns 429 after exceeding the rate limit on /api/config', async () => {
    // The rate limiter must be configured with a max of no more than 100
    // requests per window, so hammering with 200 sequential requests should
    // eventually return 429.
    let got429 = false
    for (let i = 0; i < 200; i++) {
      const res = await request(app).get('/api/config')
      if (res.status === 429) {
        got429 = true
        break
      }
    }
    expect(got429).toBe(true)
  })

  it('rate-limit response includes Retry-After or RateLimit headers', async () => {
    // Exhaust the limit
    let res
    for (let i = 0; i < 200; i++) {
      res = await request(app).get('/api/config')
      if (res.status === 429) break
    }
    // At least one of the standard rate-limit response headers must be present
    const hasHeader =
      res.headers['retry-after'] !== undefined ||
      res.headers['ratelimit-limit'] !== undefined ||
      res.headers['x-ratelimit-limit'] !== undefined
    expect(hasHeader).toBe(true)
  })
})
