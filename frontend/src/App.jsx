import { useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import { menuApi } from './lib/api'
import Home from './pages/Home'
import Order from './pages/Order'
import TrackOrder from './pages/TrackOrder'

export default function App() {
  useEffect(() => {
    const apply = (key, prop) =>
      menuApi.get(`/settings/${key}`).then(({ data }) => {
        if (data.value) document.documentElement.style.setProperty(prop, data.value)
      }).catch(() => {})
    apply('brand_primary', '--brand-primary')
    apply('brand_bg',      '--brand-bg')
    apply('brand_surface', '--brand-surface')
    apply('brand_text',    '--brand-text')
    menuApi.get('/settings/kitchen_name').then(({ data }) => {
      if (data.value) document.title = data.value
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
