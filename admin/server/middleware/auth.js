const jwt = require('jsonwebtoken')

const JWT_SECRET = process.env.JWT_SECRET || 'byteorder-dev-secret-change-in-production'

// EventSource cannot send an Authorization header, so the live order queue
// stream passes the token as ?token=. Only that route accepts it, to keep
// tokens out of URLs (and access logs) everywhere else. Paths are relative to
// where the middleware is mounted (/api/orders).
const QUERY_TOKEN_ROUTES = new Set(['/queue/stream'])

function tokenFrom(req) {
  const header = req.headers.authorization
  if (header && header.startsWith('Bearer ')) return header.slice(7)
  if (req.method === 'GET' && QUERY_TOKEN_ROUTES.has(req.path) && typeof req.query?.token === 'string') {
    return req.query.token
  }
  return null
}

function requireAuthSelfHosted(req, res, next) {
  const token = tokenFrom(req)
  if (!token) {
    return res.status(401).json({ error: 'Unauthorised' })
  }
  try {
    req.user = jwt.verify(token, JWT_SECRET, { algorithms: ['HS256'] })
    next()
  } catch {
    res.status(401).json({ error: 'Invalid token' })
  }
}

module.exports = { requireAuthSelfHosted, JWT_SECRET }
