const express = require('express')
const bcrypt = require('bcryptjs')
const jwt = require('jsonwebtoken')
const { Pool } = require('pg')
const { JWT_SECRET } = require('../middleware/auth')

const router = express.Router()
const pool = new Pool({ connectionString: process.env.DATABASE_URL || 'postgresql://byteorder:byteorder@postgres:5432/byteorder' })

// Ensure admin_users table exists and seed a default admin if empty
async function ensureAdminTable() {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS admin_users (
      id SERIAL PRIMARY KEY,
      username VARCHAR(255) UNIQUE NOT NULL,
      password_hash VARCHAR(255) NOT NULL,
      created_at TIMESTAMP DEFAULT NOW()
    )
  `)
  const { rows } = await pool.query('SELECT COUNT(*) FROM admin_users')
  if (parseInt(rows[0].count) === 0) {
    const defaultPassword = process.env.ADMIN_DEFAULT_PASSWORD || 'byteorder'
    const hash = await bcrypt.hash(defaultPassword, 12)
    await pool.query('INSERT INTO admin_users (username, password_hash) VALUES ($1, $2)', ['admin', hash])
    console.log('Default admin user created with username: admin')
  }
}

ensureAdminTable().catch(console.error)

router.post('/login', async (req, res) => {
  const { username, password } = req.body
  if (!username || !password) {
    return res.status(400).json({ error: 'Username and password required' })
  }
  try {
    const { rows } = await pool.query('SELECT * FROM admin_users WHERE username = $1', [username])
    if (!rows.length) return res.status(401).json({ error: 'Invalid credentials' })
    const user = rows[0]
    const valid = await bcrypt.compare(password, user.password_hash)
    if (!valid) return res.status(401).json({ error: 'Invalid credentials' })
    const token = jwt.sign({ id: user.id, username: user.username }, JWT_SECRET, { expiresIn: '12h', algorithm: 'HS256' })
    res.json({ token, username: user.username })
  } catch (err) {
    console.error(err)
    res.status(500).json({ error: 'Server error' })
  }
})

router.post('/change-password', async (req, res) => {
  const header = req.headers.authorization
  if (!header) return res.status(401).json({ error: 'Unauthorised' })
  try {
    const { id } = jwt.verify(header.slice(7), JWT_SECRET, { algorithms: ['HS256'] })
    const { current_password, new_password } = req.body
    const { rows } = await pool.query('SELECT * FROM admin_users WHERE id = $1', [id])
    if (!rows.length) return res.status(404).json({ error: 'User not found' })
    const valid = await bcrypt.compare(current_password, rows[0].password_hash)
    if (!valid) return res.status(401).json({ error: 'Current password incorrect' })
    const hash = await bcrypt.hash(new_password, 12)
    await pool.query('UPDATE admin_users SET password_hash = $1 WHERE id = $2', [hash, id])
    res.json({ ok: true })
  } catch {
    res.status(401).json({ error: 'Invalid token' })
  }
})

module.exports = router
