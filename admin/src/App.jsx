import { Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Layout from './components/Layout'
import OrderQueue from './pages/OrderQueue'
import OrderHistory from './pages/OrderHistory'
import MenuManagement from './pages/MenuManagement'
import Ingredients from './pages/Ingredients'
import Settings from './pages/Settings'

function RequireAuth({ children }) {
  return localStorage.getItem('token') ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<RequireAuth><Layout /></RequireAuth>}>
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
