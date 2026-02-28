import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { orderApi } from '../lib/api'

const STATUS_STEPS = ['pending', 'in_progress', 'ready']
const STATUS_LABELS = { pending: 'Order received', in_progress: 'Being prepared', ready: 'Ready to collect!' }
const STATUS_DESCRIPTIONS = {
  pending: "Your order is in the queue. Sit tight!",
  in_progress: "The chef is working on your order now.",
  ready: "Your order is ready — come and get it!",
}
const STATUS_EMOJI = { pending: '⏳', in_progress: '👨‍🍳', ready: '🎉' }

export default function TrackOrder() {
  const { orderId } = useParams()
  const navigate = useNavigate()
  const [lookupId, setLookupId] = useState('')
  const [order, setOrder] = useState(null)
  const [status, setStatus] = useState(null)
  const [queuePos, setQueuePos] = useState(null)
  const [error, setError] = useState('')
  const esRef = useRef(null)

  useEffect(() => {
    if (orderId) loadOrder(orderId)
    return () => esRef.current?.close()
  }, [orderId])

  async function loadOrder(id) {
    setError('')
    try {
      const { data } = await orderApi.get(`/orders/${id}`)
      setOrder(data)
      setStatus(data.status)
      setQueuePos(data.queue_position)
      subscribeToUpdates(id)
    } catch {
      setError('Order not found. Check your order number.')
    }
  }

  function subscribeToUpdates(id) {
    esRef.current?.close()
    const es = new EventSource(`/orders-api/orders/${id}/stream`)
    esRef.current = es
    es.onmessage = e => {
      try {
        const data = JSON.parse(e.data)
        if (data.status) setStatus(data.status)
        if (data.queue_position !== undefined) setQueuePos(data.queue_position)
      } catch {}
    }
  }

  function handleLookup(e) {
    e.preventDefault()
    if (!lookupId.trim()) return
    navigate(`/track/${lookupId.trim()}`)
  }

  const currentStep = STATUS_STEPS.indexOf(status)

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-brand-600 text-white px-4 py-4">
        <Link to="/" className="text-white text-xl">←</Link>
        <span className="text-xl font-bold ml-3">Track Order</span>
      </header>

      <div className="max-w-lg mx-auto px-4 py-8">
        {!orderId ? (
          <form onSubmit={handleLookup}>
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Find your order</h2>
            <input
              value={lookupId}
              onChange={e => setLookupId(e.target.value)}
              placeholder="Enter your order ID"
              className="w-full border-2 border-gray-200 focus:border-brand-500 rounded-xl px-4 py-3 text-lg outline-none mb-4"
            />
            <button
              type="submit"
              className="w-full bg-brand-600 hover:bg-brand-700 text-white font-bold py-3 rounded-xl text-lg"
            >
              Track
            </button>
            {error && <p className="text-red-500 text-sm mt-3">{error}</p>}
          </form>
        ) : !order ? (
          <div className="text-center py-16">
            {error ? (
              <div>
                <p className="text-red-500 mb-4">{error}</p>
                <Link to="/track" className="text-brand-600 underline">Try again</Link>
              </div>
            ) : (
              <p className="text-gray-400">Loading…</p>
            )}
          </div>
        ) : (
          <div>
            <div className="bg-white rounded-2xl shadow p-6 mb-6 text-center">
              <p className="text-5xl mb-3">{STATUS_EMOJI[status] || '📋'}</p>
              <p className="text-2xl font-extrabold text-gray-900">{order.order_number}</p>
              <p className="text-gray-500 text-lg">{order.customer_name}</p>
            </div>

            {/* Progress bar */}
            <div className="bg-white rounded-2xl shadow p-6 mb-6">
              <div className="flex items-center justify-between mb-4">
                {STATUS_STEPS.map((s, i) => (
                  <div key={s} className="flex flex-col items-center flex-1">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm mb-1 ${
                      i <= currentStep ? 'bg-brand-600 text-white' : 'bg-gray-200 text-gray-400'
                    }`}>
                      {i < currentStep ? '✓' : i + 1}
                    </div>
                    <p className={`text-xs text-center ${i <= currentStep ? 'text-brand-600 font-medium' : 'text-gray-400'}`}>
                      {STATUS_LABELS[s]}
                    </p>
                  </div>
                ))}
              </div>
              {/* Connecting line */}
              <div className="relative h-1 bg-gray-200 rounded -mt-10 mx-4 mb-6" style={{ zIndex: 0 }}>
                <div
                  className="absolute top-0 left-0 h-1 bg-brand-600 rounded transition-all duration-500"
                  style={{ width: `${(currentStep / (STATUS_STEPS.length - 1)) * 100}%` }}
                />
              </div>

              <p className="text-center text-gray-600 mt-2">{STATUS_DESCRIPTIONS[status]}</p>

              {queuePos && status === 'pending' && (
                <p className="text-center text-brand-600 font-bold mt-2">
                  You are #{queuePos} in the queue
                </p>
              )}
            </div>

            {/* Order summary */}
            <div className="bg-white rounded-2xl shadow p-6">
              <h3 className="font-bold text-gray-700 mb-3">Your order</h3>
              <div className="space-y-2">
                {order.items.map(item => (
                  <div key={item.id} className="text-sm">
                    <p className="font-medium text-gray-900">{item.menu_item_name}</p>
                    {item.ingredients.filter(i => i.included).length > 0 && (
                      <p className="text-gray-500">
                        With: {item.ingredients.filter(i => i.included).map(i => i.ingredient_name).join(', ')}
                      </p>
                    )}
                    {item.ingredients.filter(i => !i.included).length > 0 && (
                      <p className="text-red-400">
                        No: {item.ingredients.filter(i => !i.included).map(i => i.ingredient_name).join(', ')}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
