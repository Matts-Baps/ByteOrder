import { useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import { menuApi } from './lib/api'
import Home from './pages/Home'
import Order from './pages/Order'
import TrackOrder from './pages/TrackOrder'

export default function App() {
  useEffect(() => {
    menuApi.get('/settings/brand_primary').then(({ data }) => {
      if (data.value) document.documentElement.style.setProperty('--brand-primary', data.value)
    }).catch(() => {})
  }, [])

  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/order" element={<Order />} />
      <Route path="/track" element={<TrackOrder />} />
      <Route path="/track/:orderId" element={<TrackOrder />} />
    </Routes>
  )
}
