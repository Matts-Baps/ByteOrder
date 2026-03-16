// Express app factory — separated from server startup so tests can import the app
// without binding to a port.

const express = require('express')
const cors = require('cors')
const path = require('path')
const rateLimit = require('express-rate-limit')
const menuProxy = require('./routes/menu')
const orderProxy = require('./routes/orders')
const settingsProxy = require('./routes/settings')

const AUTH_MODE = process.env.AUTH_MODE || 'cloud'

let requireAuth
if (AUTH_MODE === 'cloud') {
  const requiredEnv = ['CLERK_PUBLISHABLE_KEY', 'CLERK_SECRET_KEY']
  const missingEnv = requiredEnv.filter(name => !process.env[name])
  if (missingEnv.length) {
    console.error(`FATAL: Missing required Clerk configuration: ${missingEnv.join(', ')}`)
    process.exit(1)
  }
  const clerk = require('@clerk/express')
  requireAuth = clerk.requireAuth
} else {
  const { requireAuthSelfHosted } = require('./middleware/auth')
  requireAuth = () => requireAuthSelfHosted
}

const app = express()

// Rate-limit API requests to mitigate denial-of-service attacks.
// 300 requests per minute per IP: allows normal burst navigation (a page load
// makes ~5 calls; a power user doing rapid interactions stays well under 5/sec)
// while blocking automated floods. Applied only to /api/ so static asset
// fetches don't count against the quota.
const apiLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 300,
  standardHeaders: true,  // Return RateLimit-* headers (RFC 6585 draft)
  legacyHeaders: false,
})

app.use(cors())
app.use(express.json())
app.use('/api/', apiLimiter)

if (AUTH_MODE === 'cloud') {
  const { clerkMiddleware } = require('@clerk/express')
  app.use(clerkMiddleware())
}

// Public: runtime config for the frontend
app.get('/api/config', (req, res) => {
  res.json({
    authMode: AUTH_MODE,
    clerkPublishableKey: AUTH_MODE === 'cloud' ? process.env.CLERK_PUBLISHABLE_KEY : null,
  })
})

// Self-hosted: expose login endpoint
if (AUTH_MODE === 'self-hosted') {
  app.use('/api/auth', require('./routes/auth'))
}

// Public printer endpoints — must be mounted before requireAuth()
const printersPublic = require('./routes/printers-public')
app.use('/api/orders/printers', printersPublic)

// Protected API proxies
app.use('/api/menu', requireAuth(), menuProxy)
app.use('/api/orders', requireAuth(), orderProxy)
app.use('/api/settings', requireAuth(), settingsProxy)

// Serve built frontend in production
if (process.env.NODE_ENV === 'production') {
  app.use(express.static(path.join(__dirname, '../dist')))
  app.get('*', (req, res) => res.sendFile(path.join(__dirname, '../dist/index.html')))
}

module.exports = app
