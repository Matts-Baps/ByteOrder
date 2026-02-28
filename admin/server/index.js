// OpenTelemetry — must be required before anything else
if (process.env.OTEL_ENDPOINT) {
  require('./telemetry')
}

const express = require('express')
const cors = require('cors')
const path = require('path')
const authRoutes = require('./routes/auth')
const menuProxy = require('./routes/menu')
const orderProxy = require('./routes/orders')
const settingsProxy = require('./routes/settings')
const { requireAuth } = require('./middleware/auth')

// Startup security check — refuse weak JWT secret in production.
// ADMIN_DEFAULT_PASSWORD is a one-time DB seed value (only used when the
// admin_users table is empty) so it is not checked here; change the admin
// password via the UI after first login instead.
const KNOWN_WEAK_JWT = new Set([
  '', 'change-me-in-production', 'byteorder-dev-secret-change-in-production', 'byteorder',
])
if (process.env.NODE_ENV === 'production') {
  if (KNOWN_WEAK_JWT.has(process.env.JWT_SECRET || '')) {
    console.error('FATAL: JWT_SECRET is missing or is a known default. Set a strong unique secret before running in production.')
    process.exit(1)
  }
}

const app = express()
const PORT = process.env.PORT || 3001

app.use(cors())
app.use(express.json())

// Auth (public)
app.use('/api/auth', authRoutes)

// Protected API proxies
app.use('/api/menu', requireAuth, menuProxy)
app.use('/api/orders', requireAuth, orderProxy)
app.use('/api/settings', requireAuth, settingsProxy)

// Serve built frontend in production
if (process.env.NODE_ENV === 'production') {
  app.use(express.static(path.join(__dirname, '../dist')))
  app.get('*', (req, res) => res.sendFile(path.join(__dirname, '../dist/index.html')))
}

app.listen(PORT, () => console.log(`Admin server running on :${PORT}`))
