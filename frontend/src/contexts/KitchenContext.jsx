import { createContext, useContext, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { menuApi, orderApi, setKitchenId } from '../lib/api'

const KitchenContext = createContext(null)

export function useKitchen() {
  return useContext(KitchenContext)
}

export function KitchenProvider({ children }) {
  const { slug } = useParams()
  const [kitchenId, setKitchenIdState] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!slug) return
    menuApi.get(`/slug/${slug}`)
      .then(({ data }) => {
        setKitchenId(data.kitchen_id)
        setKitchenIdState(data.kitchen_id)
        // Apply brand settings and page title now that kitchen_id header is set
        const apply = (key, prop) =>
          menuApi.get(`/settings/${key}`).then(({ data: s }) => {
            if (s.value) document.documentElement.style.setProperty(prop, s.value)
          }).catch(() => {})
        apply('brand_primary', '--brand-primary')
        apply('brand_bg',      '--brand-bg')
        apply('brand_surface', '--brand-surface')
        apply('brand_text',    '--brand-text')
        menuApi.get('/settings/kitchen_name').then(({ data: s }) => {
          if (s.value) document.title = s.value
        }).catch(() => {})
      })
      .catch(() => setError('Kitchen not found'))
  }, [slug])

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-800 mb-2">Kitchen not found</h1>
          <p className="text-gray-500">Check the URL and try again.</p>
        </div>
      </div>
    )
  }

  if (!kitchenId) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-8 h-8 border-4 border-brand-600 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <KitchenContext.Provider value={{ kitchenId, slug }}>
      {children}
    </KitchenContext.Provider>
  )
}
