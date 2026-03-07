// OpenTelemetry — must be required before anything else
if (process.env.OTEL_ENDPOINT) {
  require('./telemetry')
}

const express = require('express')
const cors = require('cors')
const path = require('path')
const { clerkMiddleware, requireAuth } = require('@clerk/express')
const menuProxy = require('./routes/menu')
const orderProxy = require('./routes/orders')
const settingsProxy = require('./routes/settings')

const app = express()
const PORT = process.env.PORT || 3001

app.use(cors())
app.use(express.json())
app.use(clerkMiddleware())

// Public: exposes only the publishable key (safe to include in browser)
app.get('/api/config', (req, res) => {
  res.json({ clerkPublishableKey: process.env.CLERK_PUBLISHABLE_KEY })
})

// Protected API proxies
app.use('/api/menu', requireAuth(), menuProxy)
app.use('/api/orders', requireAuth(), orderProxy)
app.use('/api/settings', requireAuth(), settingsProxy)

// Serve built frontend in production
if (process.env.NODE_ENV === 'production') {
  app.use(express.static(path.join(__dirname, '../dist')))
  app.get('*', (req, res) => res.sendFile(path.join(__dirname, '../dist/index.html')))
}

app.listen(PORT, () => console.log(`Admin server running on :${PORT}`))
