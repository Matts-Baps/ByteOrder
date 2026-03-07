import { Routes, Route, Navigate } from 'react-router-dom'
import { SignedIn, SignedOut, RedirectToSignIn } from '@clerk/clerk-react'
import Layout from './components/Layout'
import OrderQueue from './pages/OrderQueue'
import OrderHistory from './pages/OrderHistory'
import MenuManagement from './pages/MenuManagement'
import Ingredients from './pages/Ingredients'
import Settings from './pages/Settings'

function ProtectedLayout() {
  return (
    <>
      <SignedIn><Layout /></SignedIn>
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
