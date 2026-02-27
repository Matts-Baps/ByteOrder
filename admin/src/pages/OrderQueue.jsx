import { useState, useEffect, useCallback, useRef } from 'react'
import api from '../lib/api'

const STATUS_LABELS = { pending: 'Pending', in_progress: 'Cooking', ready: 'Ready', completed: 'Done' }
const STATUS_COLOURS = {
  pending: 'bg-yellow-100 text-yellow-800',
  in_progress: 'bg-blue-100 text-blue-800',
  ready: 'bg-green-100 text-green-800',
  completed: 'bg-gray-100 text-gray-600',
}
const NEXT_STATUS = { pending: 'in_progress', in_progress: 'ready', ready: 'completed' }
const NEXT_LABEL = { pending: 'Start Cooking', in_progress: 'Mark Ready', ready: 'Complete' }

export default function OrderQueue() {
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchQueue = useCallback(async () => {
    try {
      const { data } = await api.get('/orders/queue')
      setOrders(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchQueue()
    const interval = setInterval(fetchQueue, 10000)

    const token = localStorage.getItem('token')
    const es = new EventSource(`/api/orders/queue/stream?token=${encodeURIComponent(token)}`)
    es.onmessage = () => fetchQueue()
    es.onerror = () => {}   // polling handles reconnection

    return () => { clearInterval(interval); es.close() }
  }, [fetchQueue])

  async function advance(order) {
    const next = NEXT_STATUS[order.status]
    if (!next) return
    await api.put(`/orders/${order.id}/status`, { status: next })
    fetchQueue()
  }

  if (loading) return <p className="text-gray-500">Loading queue…</p>

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold text-gray-900">Order Queue</h1>
        <button onClick={fetchQueue} className="text-sm text-orange-600 hover:underline">Refresh</button>
      </div>

      {orders.length === 0 && (
        <div className="text-center py-16 text-gray-400">No active orders</div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {orders.map(order => (
          <div key={order.id} className="bg-white rounded-xl shadow p-4 flex flex-col gap-3">
            <div className="flex items-start justify-between">
              <div>
                <p className="font-bold text-lg text-gray-900">{order.order_number}</p>
                <p className="text-gray-600">{order.customer_name}</p>
              </div>
              <span className={`text-xs font-semibold px-2 py-1 rounded-full ${STATUS_COLOURS[order.status]}`}>
                {STATUS_LABELS[order.status]}
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

            {NEXT_STATUS[order.status] && (
              <button
                onClick={() => advance(order)}
                className="mt-auto w-full bg-orange-600 hover:bg-orange-700 text-white text-sm font-semibold py-2 rounded-lg transition-colors"
              >
                {NEXT_LABEL[order.status]}
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
