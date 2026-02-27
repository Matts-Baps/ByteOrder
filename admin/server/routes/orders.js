const http = require('http')
const express = require('express')
const axios = require('axios')
const jwt = require('jsonwebtoken')
const { JWT_SECRET } = require('../middleware/auth')

const router = express.Router()
const ORDER_SERVICE = process.env.ORDER_SERVICE_URL || 'http://order-service:8001'

// SSE proxy — must come before router.all() since axios buffers and cannot proxy SSE
router.get('/queue/stream', (req, res) => {
  const token = req.headers.authorization?.slice(7) || req.query.token
  try { jwt.verify(token, JWT_SECRET) }
  catch { return res.status(401).json({ error: 'Unauthorised' }) }

  res.setHeader('Content-Type', 'text/event-stream')
  res.setHeader('Cache-Control', 'no-cache')
  res.setHeader('Connection', 'keep-alive')
  res.flushHeaders()

  const urlObj = new URL(`${ORDER_SERVICE}/orders/queue/stream`)
  const proxyReq = http.get(
    { hostname: urlObj.hostname, port: parseInt(urlObj.port) || 80, path: urlObj.pathname },
    (proxyRes) => {
      proxyRes.pipe(res)
      req.on('close', () => proxyRes.destroy())
    }
  )
  proxyReq.on('error', () => res.end())
})

router.all('/*', async (req, res) => {
  try {
    const response = await axios({
      method: req.method,
      url: `${ORDER_SERVICE}/orders${req.path}`,
      params: req.query,
      data: req.body,
      headers: { 'Content-Type': 'application/json' },
    })
    res.status(response.status).json(response.data)
  } catch (err) {
    const status = err.response?.status || 500
    res.status(status).json(err.response?.data || { error: 'Order service error' })
  }
})

module.exports = router
