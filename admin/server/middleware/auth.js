const jwt = require('jsonwebtoken')

const JWT_SECRET = process.env.JWT_SECRET || 'byteorder-dev-secret-change-in-production'

function requireAuthSelfHosted(req, res, next) {
  const header = req.headers.authorization
  if (!header || !header.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Unauthorised' })
  }
  try {
    req.user = jwt.verify(header.slice(7), JWT_SECRET, { algorithms: ['HS256'] })
    next()
  } catch {
    res.status(401).json({ error: 'Invalid token' })
  }
}

module.exports = { requireAuthSelfHosted, JWT_SECRET }
