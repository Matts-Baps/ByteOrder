// OpenTelemetry — must be required before anything else
if (process.env.OTEL_ENDPOINT) {
  require('./telemetry')
}

const express = require('express')
const cors = require('cors')
const path = require('path')
const menuProxy = require('./routes/menu')
const orderProxy = require('./routes/orders')
const settingsProxy = require('./routes/settings')

const AUTH_MODE = process.env.AUTH_MODE || 'cloud'

// ── Cloud mode: Clerk ─────────────────────────────────────────────────────────
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
  // ── Self-hosted mode: JWT env-var auth ──────────────────────────────────────
  const { requireAuthSelfHosted } = require('./middleware/auth')
  requireAuth = () => requireAuthSelfHosted
}

const app = express()
const PORT = process.env.PORT || 3001

app.use(cors())
app.use(express.json())

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

// Protected API proxies
app.use('/api/menu', requireAuth(), menuProxy)
app.use('/api/orders', requireAuth(), orderProxy)
app.use('/api/settings', requireAuth(), settingsProxy)

// Serve built frontend in production
if (process.env.NODE_ENV === 'production') {
  app.use(express.static(path.join(__dirname, '../dist')))
  app.get('*', (req, res) => res.sendFile(path.join(__dirname, '../dist/index.html')))
}

app.listen(PORT, () => console.log(`Admin server running on :${PORT} (auth: ${AUTH_MODE})`))
