const http = require('http')
const express = require('express')
const axios = require('axios')

const router = express.Router()
const ORDER_SERVICE = process.env.ORDER_SERVICE_URL || 'http://order-service:8001'
const AUTH_MODE = process.env.AUTH_MODE || 'cloud'

function getKitchenId(req) {
  return AUTH_MODE === 'self-hosted'
    ? (process.env.DEFAULT_KITCHEN_ID || 'default')
    : req.auth?.orgId
}

// SSE proxy — must come before router.all() since axios buffers and cannot proxy SSE.
// Auth is already enforced by requireAuth() in index.js before this router is reached.
router.get('/queue/stream', (req, res) => {
  const kitchenId = getKitchenId(req)
  if (!kitchenId) {
    return res.status(403).json({ error: 'No organization selected' })
  }

  res.setHeader('Content-Type', 'text/event-stream')
  res.setHeader('Cache-Control', 'no-cache')
  res.setHeader('Connection', 'keep-alive')
  res.flushHeaders()

  const urlObj = new URL(`${ORDER_SERVICE}/orders/queue/stream`)
  const proxyReq = http.get(
    {
      hostname: urlObj.hostname,
      port: parseInt(urlObj.port) || 80,
      path: urlObj.pathname,
      headers: { 'X-Kitchen-ID': kitchenId },
    },
    (proxyRes) => {
      proxyRes.pipe(res)
      req.on('close', () => proxyRes.destroy())
    }
  )
  proxyReq.on('error', () => res.end())
})

router.all('/*', async (req, res) => {
  const kitchenId = getKitchenId(req)
  if (!kitchenId) {
    return res.status(403).json({ error: 'No organization selected' })
  }
  try {
    const response = await axios({
      method: req.method,
      url: `${ORDER_SERVICE}/orders${req.path}`,
      params: req.query,
      data: req.body,
      headers: { 'Content-Type': 'application/json', 'X-Kitchen-ID': kitchenId },
    })
    res.status(response.status).json(response.data)
  } catch (err) {
    const status = err.response?.status || 500
    res.status(status).json(err.response?.data || { error: 'Order service error' })
  }
})

module.exports = router
