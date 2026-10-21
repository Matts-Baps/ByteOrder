const jwt = require('jsonwebtoken')
const { requireAuthSelfHosted, JWT_SECRET } = require('../server/middleware/auth')

function token() {
  return jwt.sign({ username: 'admin' }, JWT_SECRET, { expiresIn: '1h', algorithm: 'HS256' })
}

function run({ method = 'GET', path = '/', headers = {}, query = {} }) {
  const req = { method, path, headers, query }
  const res = {
    statusCode: 200,
    status(code) { this.statusCode = code; return this },
    json() { return this },
  }
  const next = jest.fn()
  requireAuthSelfHosted(req, res, next)
  return { req, res, next }
}

describe('requireAuthSelfHosted', () => {
  it('accepts a Bearer token header', () => {
    const { next, req } = run({ headers: { authorization: `Bearer ${token()}` } })
    expect(next).toHaveBeenCalled()
    expect(req.user.username).toBe('admin')
  })

  it('rejects a missing token', () => {
    const { next, res } = run({})
    expect(next).not.toHaveBeenCalled()
    expect(res.statusCode).toBe(401)
  })

  it('rejects an invalid token', () => {
    const { next, res } = run({ headers: { authorization: 'Bearer nope' } })
    expect(next).not.toHaveBeenCalled()
    expect(res.statusCode).toBe(401)
  })

  // EventSource cannot send headers, so the live order stream passes the token
  // in the query string. Only that route may do so (#54).
  it('accepts ?token= on the order queue stream', () => {
    const { next } = run({ path: '/queue/stream', query: { token: token() } })
    expect(next).toHaveBeenCalled()
  })

  it('rejects an invalid ?token= on the order queue stream', () => {
    const { next, res } = run({ path: '/queue/stream', query: { token: 'nope' } })
    expect(next).not.toHaveBeenCalled()
    expect(res.statusCode).toBe(401)
  })

  it('ignores ?token= on any other route', () => {
    const { next, res } = run({ path: '/', query: { token: token() } })
    expect(next).not.toHaveBeenCalled()
    expect(res.statusCode).toBe(401)
  })

  it('ignores ?token= on the stream for non-GET requests', () => {
    const { next } = run({ method: 'POST', path: '/queue/stream', query: { token: token() } })
    expect(next).not.toHaveBeenCalled()
  })
})
