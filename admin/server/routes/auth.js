const express = require('express')
const jwt = require('jsonwebtoken')
const { JWT_SECRET } = require('../middleware/auth')

const router = express.Router()

router.post('/login', (req, res) => {
  const { username, password } = req.body
  if (!username || !password) {
    return res.status(400).json({ error: 'Username and password required' })
  }

  const validUsername = process.env.ADMIN_USERNAME || 'admin'
  const validPassword = process.env.ADMIN_PASSWORD || 'byteorder'

  if (username !== validUsername || password !== validPassword) {
    return res.status(401).json({ error: 'Invalid credentials' })
  }

  const token = jwt.sign({ username }, JWT_SECRET, { expiresIn: '12h', algorithm: 'HS256' })
  res.json({ token, username })
})

module.exports = router
