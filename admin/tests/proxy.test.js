const request = require('supertest')
const jwt = require('jsonwebtoken')

process.env.AUTH_MODE = 'self-hosted'
process.env.ADMIN_USERNAME = 'admin'
process.env.ADMIN_PASSWORD = 'testpass'

// JWT_SECRET must match what the middleware uses
const JWT_SECRET = process.env.JWT_SECRET || 'byteorder-dev-secret-change-in-production'

// Mock axios before requiring app so all route handlers use the mock
jest.mock('axios')
const axios = require('axios')

const app = require('../server/app')

function makeToken(username = 'admin') {
  return jwt.sign({ username }, JWT_SECRET, { expiresIn: '1h', algorithm: 'HS256' })
}

beforeEach(() => {
  jest.clearAllMocks()
})

// ── Unauthenticated requests ──────────────────────────────────────────────────

describe('Unauthenticated requests are rejected', () => {
  it('rejects GET /api/menu/ without token', async () => {
    const res = await request(app).get('/api/menu/')
    expect(res.status).toBe(401)
  })

  it('rejects GET /api/orders/ without token', async () => {
    const res = await request(app).get('/api/orders/')
    expect(res.status).toBe(401)
  })

  it('rejects GET /api/settings/ without token', async () => {
    const res = await request(app).get('/api/settings/')
    expect(res.status).toBe(401)
  })
})

// ── Menu proxy ────────────────────────────────────────────────────────────────

describe('GET /api/menu/* proxies to menu-service', () => {
  it('forwards authenticated request and returns proxied data', async () => {
    const mockCategories = [{ id: 1, name: 'Burgers' }]
    axios.mockResolvedValueOnce({ status: 200, data: mockCategories })

    const token = makeToken()
    const res = await request(app)
      .get('/api/menu/categories/')
      .set('Authorization', `Bearer ${token}`)

    expect(res.status).toBe(200)
    expect(res.body).toEqual(mockCategories)
    expect(axios).toHaveBeenCalledTimes(1)
    const callArg = axios.mock.calls[0][0]
    expect(callArg.url).toContain('/categories/')
    expect(callArg.headers['X-Kitchen-ID']).toBeDefined()
  })

  it('propagates upstream error status', async () => {
    const err = new Error('Not found')
    err.response = { status: 404, data: { detail: 'Not found' } }
    axios.mockRejectedValueOnce(err)

    const token = makeToken()
    const res = await request(app)
      .get('/api/menu/categories/9999')
      .set('Authorization', `Bearer ${token}`)

    expect(res.status).toBe(404)
  })
})

// ── Orders proxy ──────────────────────────────────────────────────────────────

describe('GET /api/orders/* proxies to order-service', () => {
  it('forwards authenticated request and returns proxied data', async () => {
    const mockOrders = [{ id: 1, customer_name: 'Alice', status: 'pending' }]
    axios.mockResolvedValueOnce({ status: 200, data: mockOrders })

    const token = makeToken()
    const res = await request(app)
      .get('/api/orders/queue')
      .set('Authorization', `Bearer ${token}`)

    expect(res.status).toBe(200)
    expect(res.body).toEqual(mockOrders)
    const callArg = axios.mock.calls[0][0]
    expect(callArg.url).toContain('/orders/queue')
  })
})

// ── Settings proxy ────────────────────────────────────────────────────────────

describe('GET /api/settings/* proxies to menu-service settings', () => {
  it('forwards authenticated request and returns proxied data', async () => {
    const mockSetting = { key: 'kitchen_name', value: 'My Kitchen' }
    axios.mockResolvedValueOnce({ status: 200, data: mockSetting })

    const token = makeToken()
    const res = await request(app)
      .get('/api/settings/kitchen_name')
      .set('Authorization', `Bearer ${token}`)

    expect(res.status).toBe(200)
    expect(res.body).toEqual(mockSetting)
    const callArg = axios.mock.calls[0][0]
    expect(callArg.url).toContain('/settings/kitchen_name')
  })
})
