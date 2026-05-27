const express = require('express')
const axios = require('axios')

const router = express.Router()
const MENU_SERVICE = process.env.MENU_SERVICE_URL || 'http://menu-service:8000'
const AUTH_MODE = process.env.AUTH_MODE || 'cloud'

function getKitchenId(req) {
  if (AUTH_MODE === 'self-hosted') return process.env.DEFAULT_KITCHEN_ID || 'default'
  // @clerk/express v2: req.auth is a function, not an object — must call it.
  const auth = req.auth?.()
  return auth?.orgId || auth?.userId
}

router.all('/{*path}', async (req, res) => {
  const kitchenId = getKitchenId(req)
  if (!kitchenId) {
    return res.status(403).json({ error: 'No organization selected' })
  }
  try {
    const response = await axios({
      method: req.method,
      url: `${MENU_SERVICE}/settings${req.path}`,
      params: req.query,
      data: req.body,
      headers: { 'Content-Type': 'application/json', 'X-Kitchen-ID': kitchenId },
    })
    res.status(response.status).json(response.data)
  } catch (err) {
    const status = err.response?.status || 500
    res.status(status).json(err.response?.data || { error: 'Settings error' })
  }
})

module.exports = router
