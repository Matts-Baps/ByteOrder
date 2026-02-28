import { useEffect } from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import api from '../lib/api'

const nav = [
  { to: '/orders', label: 'Order Queue' },
  { to: '/history', label: 'Order History' },
  { to: '/menu', label: 'Menu' },
  { to: '/ingredients', label: 'Ingredients' },
  { to: '/settings', label: 'Settings' },
]

export default function Layout() {
  const navigate = useNavigate()

  useEffect(() => {
    api.get('/settings/brand_primary').then(({ data }) => {
      if (data.value) document.documentElement.style.setProperty('--brand-primary', data.value)
    }).catch(() => {})
  }, [])

  function logout() {
    localStorage.removeItem('token')
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-brand-600 text-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <span className="text-xl font-bold tracking-tight">ByteOrder Admin</span>
          <button onClick={logout} className="text-sm underline hover:no-underline">Log out</button>
        </div>
      </header>

      <nav className="bg-white border-b shadow-sm">
        <div className="max-w-7xl mx-auto px-4 flex gap-1">
          {nav.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  isActive
                    ? 'border-brand-600 text-brand-600'
                    : 'border-transparent text-gray-600 hover:text-brand-600'
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </div>
      </nav>

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
