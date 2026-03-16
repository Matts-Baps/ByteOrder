/**
 * Public printer endpoints — no kitchen auth required.
 *
 * These are proxied directly to the order-service without adding X-Kitchen-ID.
 * - POST /register  — Pi calls this on boot to register itself (idempotent)
 * - GET  /stream    — Pi calls this to receive print jobs (auth via Bearer MAC token)
 *
 * Mounted at /api/orders/printers before requireAuth() so Pi devices can reach
 * them without a user session.
 */
const http = require('http')
const axios = require('axios')
const express = require('express')

const router = express.Router()
const ORDER_SERVICE = process.env.ORDER_SERVICE_URL || 'http://order-service:8001'

router.post('/register', async (req, res) => {
  try {
    const response = await axios.post(
      `${ORDER_SERVICE}/orders/printers/register`,
      req.body,
      { headers: { 'Content-Type': 'application/json' } },
    )
    res.status(response.status).json(response.data)
  } catch (err) {
    const status = err.response?.status || 500
    res.status(status).json(err.response?.data || { error: 'Order service error' })
  }
})

router.get('/stream', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream')
  res.setHeader('Cache-Control', 'no-cache')
  res.setHeader('Connection', 'keep-alive')
  res.flushHeaders()

  const urlObj = new URL(`${ORDER_SERVICE}/orders/printers/stream`)
  const proxyReq = http.get(
    {
      hostname: urlObj.hostname,
      port: parseInt(urlObj.port) || 80,
      path: urlObj.pathname,
      headers: { Authorization: req.headers.authorization || '' },
    },
    (proxyRes) => {
      proxyRes.pipe(res)
      req.on('close', () => proxyRes.destroy())
    },
  )
  proxyReq.on('error', () => res.end())
})

module.exports = router
