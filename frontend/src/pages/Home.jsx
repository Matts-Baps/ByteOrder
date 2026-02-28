import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { QRCodeSVG } from 'qrcode.react'
import { orderApi, menuApi } from '../lib/api'

export default function Home() {
  const [queue, setQueue] = useState([])
  const [kitchenName, setKitchenName] = useState('ByteOrder Kitchen')
  const [logo, setLogo] = useState('')
  const [brandColor, setBrandColor] = useState('#ea580c')
  const [orderUrl, setOrderUrl] = useState('')
  const esRef = useRef(null)

  useEffect(() => {
    menuApi.get('/settings/kitchen_name').then(({ data }) => {
      if (data.value) setKitchenName(data.value)
    }).catch(() => {})

    menuApi.get('/settings/logo').then(({ data }) => {
      if (data.value) setLogo(data.value)
    }).catch(() => {})

    menuApi.get('/settings/brand_primary').then(({ data }) => {
      if (data.value) setBrandColor(data.value)
    }).catch(() => {})

    menuApi.get('/settings/frontend_url').then(({ data }) => {
      const base = data.value || window.location.origin
      setOrderUrl(`${base.replace(/\/$/, '')}/order`)
    }).catch(() => {
      setOrderUrl(`${window.location.origin}/order`)
    })

    loadQueue()

    // Subscribe to queue updates via SSE
    const es = new EventSource('/orders-api/orders/queue/stream')
    esRef.current = es
    es.onmessage = () => loadQueue()

    return () => es.close()
  }, [])

  async function loadQueue() {
    try {
      const { data } = await orderApi.get('/orders/queue')
      setQueue(data)
    } catch {
      setQueue([])
    }
  }

  const STATUS_COLOURS = {
    pending: 'bg-yellow-400',
    in_progress: 'bg-blue-500',
    ready: 'bg-green-500',
  }
  const STATUS_LABELS = { pending: 'Waiting', in_progress: 'Cooking', ready: 'Ready!' }

  return (
    <div className="min-h-screen bg-brand-50 flex flex-col items-center justify-center px-4 py-10">
      {logo
        ? <img src={logo} alt={kitchenName} className="h-20 w-auto object-contain mb-3" />
        : <h1 className="text-4xl font-extrabold text-brand-600 mb-1 tracking-tight">{kitchenName}</h1>
      }
      <p className="text-gray-500 mb-10 text-lg">Scan to order from your phone</p>

      <div className="bg-white rounded-2xl shadow-xl p-6 mb-10">
        {orderUrl ? (
          <QRCodeSVG value={orderUrl} size={220} fgColor={brandColor} />
        ) : (
          <div className="w-[220px] h-[220px] bg-gray-100 rounded animate-pulse" />
        )}
        <p className="text-center text-sm text-gray-400 mt-3">
          or <Link to="/order" className="text-brand-600 underline">tap here</Link> to order
        </p>
      </div>

      <div className="w-full max-w-md">
        <h2 className="text-xl font-bold text-gray-800 mb-3">Live Queue</h2>
        {queue.length === 0 ? (
          <p className="text-gray-400 text-center py-4">No active orders — be the first!</p>
        ) : (
          <div className="space-y-2">
            {queue.map(order => (
              <div key={order.id} className="bg-white rounded-xl shadow px-4 py-3 flex items-center justify-between">
                <div>
                  <span className="font-bold text-gray-900">{order.order_number}</span>
                  <span className="text-gray-500 ml-2">{order.customer_name}</span>
                </div>
                <span className={`text-white text-xs font-semibold px-3 py-1 rounded-full ${STATUS_COLOURS[order.status] || 'bg-gray-400'}`}>
                  {STATUS_LABELS[order.status] || order.status}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="mt-8 flex gap-4">
        <Link
          to="/order"
          className="bg-brand-600 hover:bg-brand-700 text-white font-bold px-8 py-3 rounded-xl text-lg shadow transition-colors"
        >
          Place Order
        </Link>
        <Link
          to="/track"
          className="bg-white hover:bg-gray-50 text-brand-600 font-bold px-8 py-3 rounded-xl text-lg shadow border border-brand-200 transition-colors"
        >
          Track Order
        </Link>
      </div>
    </div>
  )
}
