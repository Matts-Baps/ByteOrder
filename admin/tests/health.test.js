const request = require('supertest')

// Set auth mode before requiring the app so middleware is configured correctly
process.env.AUTH_MODE = 'self-hosted'
process.env.ADMIN_USERNAME = 'admin'
process.env.ADMIN_PASSWORD = 'testpass'

const app = require('../server/app')

describe('GET /api/config', () => {
  it('returns authMode and clerkPublishableKey fields', async () => {
    const res = await request(app).get('/api/config')
    expect(res.status).toBe(200)
    expect(res.body).toHaveProperty('authMode')
    expect(res.body).toHaveProperty('clerkPublishableKey')
  })

  it('returns authMode=self-hosted when AUTH_MODE is self-hosted', async () => {
    const res = await request(app).get('/api/config')
    expect(res.body.authMode).toBe('self-hosted')
  })

  it('returns null clerkPublishableKey in self-hosted mode', async () => {
    const res = await request(app).get('/api/config')
    expect(res.body.clerkPublishableKey).toBeNull()
  })
})
