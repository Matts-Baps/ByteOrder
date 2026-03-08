import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { SignedIn, SignedOut, RedirectToSignIn, useAuth, useClerk } from '@clerk/clerk-react'
import Layout from './components/Layout'
import { setupApiInterceptors } from './lib/api'

// Registers Axios interceptors using Clerk's React APIs after the session
// is available. Rendered once inside <SignedIn> so hooks are always valid.
function ApiSetup() {
  const { getToken } = useAuth()
  const { openSignIn } = useClerk()
  useEffect(() => setupApiInterceptors({ getToken, openSignIn }), [getToken, openSignIn])
  return null
}
import OrderQueue from './pages/OrderQueue'
import OrderHistory from './pages/OrderHistory'
import MenuManagement from './pages/MenuManagement'
import Ingredients from './pages/Ingredients'
import Settings from './pages/Settings'

function ProtectedLayout() {
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

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<ProtectedLayout />}>
        <Route index element={<Navigate to="/orders" replace />} />
        <Route path="orders" element={<OrderQueue />} />
        <Route path="history" element={<OrderHistory />} />
        <Route path="menu" element={<MenuManagement />} />
        <Route path="ingredients" element={<Ingredients />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  )
}
