const request = require('supertest')

process.env.AUTH_MODE = 'self-hosted'
process.env.ADMIN_USERNAME = 'testadmin'
process.env.ADMIN_PASSWORD = 'testpass123'

const app = require('../server/app')

describe('POST /api/auth/login', () => {
  it('returns a token for correct credentials', async () => {
    const res = await request(app)
      .post('/api/auth/login')
      .send({ username: 'testadmin', password: 'testpass123' })

    expect(res.status).toBe(200)
    expect(res.body).toHaveProperty('token')
    expect(res.body).toHaveProperty('username', 'testadmin')
    expect(typeof res.body.token).toBe('string')
    expect(res.body.token.length).toBeGreaterThan(0)
  })

  it('returns 401 for wrong password', async () => {
    const res = await request(app)
      .post('/api/auth/login')
      .send({ username: 'testadmin', password: 'wrongpass' })

    expect(res.status).toBe(401)
    expect(res.body).toHaveProperty('error')
  })

  it('returns 401 for wrong username', async () => {
    const res = await request(app)
      .post('/api/auth/login')
      .send({ username: 'hacker', password: 'testpass123' })

    expect(res.status).toBe(401)
  })

  it('returns 400 when credentials are missing', async () => {
    const res = await request(app)
      .post('/api/auth/login')
      .send({})

    expect(res.status).toBe(400)
  })
})
