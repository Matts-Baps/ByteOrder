import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { SignedIn, SignedOut, RedirectToSignIn, useAuth, useClerk } from '@clerk/clerk-react'
import Layout from './components/Layout'
import { setupApiInterceptors, setupSelfHostedInterceptors } from './lib/api'
import Login from './pages/Login'
import OrderQueue from './pages/OrderQueue'
import OrderHistory from './pages/OrderHistory'
import MenuManagement from './pages/MenuManagement'
import Ingredients from './pages/Ingredients'
import Printers from './pages/Printers'
import Settings from './pages/Settings'

// ── Cloud: Clerk-backed protected layout ──────────────────────────────────────
// Only rendered when ClerkProvider is present (authMode === 'cloud'), so hooks are safe.
function ApiSetup() {
  const { getToken } = useAuth()
  const { openSignIn } = useClerk()
  useEffect(() => setupApiInterceptors({ getToken, openSignIn }), [getToken, openSignIn])
  return null
}

function CloudProtectedLayout() {
  return (
    <>
      <SignedIn>
        <ApiSetup />
        <Layout />
      </SignedIn>
      <SignedOut><RedirectToSignIn /></SignedOut>
    </>
  )
}

// ── Self-hosted: localStorage JWT protected layout ────────────────────────────
function SelfHostedProtectedLayout() {
  useEffect(() => setupSelfHostedInterceptors(), [])
  return localStorage.getItem('token') ? <Layout /> : <Navigate to="/login" replace />
}

export default function App({ authMode }) {
  const isCloud = authMode === 'cloud'
  return (
    <Routes>
      {!isCloud && <Route path="/login" element={<Login />} />}
      <Route
        path="/"
        element={isCloud ? <CloudProtectedLayout /> : <SelfHostedProtectedLayout />}
      >
        <Route index element={<Navigate to="/orders" replace />} />
        <Route path="orders" element={<OrderQueue />} />
        <Route path="history" element={<OrderHistory />} />
        <Route path="menu" element={<MenuManagement />} />
        <Route path="ingredients" element={<Ingredients />} />
        <Route path="printers" element={<Printers />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  )
}
