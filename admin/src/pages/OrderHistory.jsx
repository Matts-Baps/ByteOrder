import { useState, useEffect } from 'react'
import api from '../lib/api'

function todayStr() {
  return new Date().toISOString().slice(0, 10)
}

export default function OrderHistory() {
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [date, setDate] = useState(todayStr())

  async function fetchHistory(d) {
    setLoading(true)
    try {
      const { data } = await api.get('/orders/history', { params: { date: d } })
      setOrders(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchHistory(date) }, [date])

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold text-gray-900">Order History</h1>
        <input
          type="date"
          value={date}
          onChange={e => setDate(e.target.value)}
          className="border rounded px-3 py-1.5 text-sm"
        />
      </div>

      {loading && <p className="text-gray-500">Loading…</p>}

      {!loading && orders.length === 0 && (
        <div className="text-center py-16 text-gray-400">No completed orders for this date</div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {orders.map(order => (
          <div key={order.id} className="bg-white rounded-xl shadow p-4 flex flex-col gap-3">
            <div className="flex items-start justify-between">
              <div>
                <p className="font-bold text-lg text-gray-900">{order.order_number}</p>
                <p className="text-gray-600">{order.customer_name}</p>
              </div>
              <span className="text-xs text-gray-400">
                {new Date(order.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>

            <div className="divide-y divide-gray-100 text-sm">
              {order.items.map(item => (
                <div key={item.id} className="py-2">
                  <p className="font-medium text-gray-800">{item.menu_item_name}</p>
                  {item.ingredients.filter(i => i.included).length > 0 && (
                    <p className="text-gray-500">
                      With: {item.ingredients.filter(i => i.included).map(i => i.ingredient_name).join(', ')}
                    </p>
                  )}
                  {item.ingredients.filter(i => !i.included).length > 0 && (
                    <p className="text-red-500">
                      NO: {item.ingredients.filter(i => !i.included).map(i => i.ingredient_name).join(', ')}
                    </p>
                  )}
                  {item.options.length > 0 && (
                    <p className="text-gray-500">
                      {item.options.map(o => `${o.group_name}: ${o.option_name}`).join(' · ')}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
