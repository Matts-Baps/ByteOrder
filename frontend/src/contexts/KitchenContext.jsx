import { createContext, useContext, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { menuApi, orderApi, setKitchenId } from '../lib/api'

const KitchenContext = createContext(null)

export function useKitchen() {
  return useContext(KitchenContext)
}

function loadBrandSettings() {
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
}

/**
 * KitchenProvider resolves the active kitchen in one of two ways:
 *
 * Cloud (slug-based):   rendered inside /k/:slug/* — reads slug from URL params,
 *                        calls GET /slug/:slug to resolve kitchen_id.
 *
 * Self-hosted (direct): pass fixedKitchenId="default" — skips the slug lookup
 *                        and uses the ID directly. slug will be null in context.
 */
export function KitchenProvider({ children, fixedKitchenId = null }) {
  const params = useParams()
  const slug = fixedKitchenId ? null : (params.slug ?? null)
  const [kitchenId, setKitchenIdState] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (fixedKitchenId) {
      setKitchenId(fixedKitchenId)
      setKitchenIdState(fixedKitchenId)
      loadBrandSettings()
      return
    }
    if (!slug) return
    menuApi.get(`/slug/${slug}`)
      .then(({ data }) => {
        setKitchenId(data.kitchen_id)
        setKitchenIdState(data.kitchen_id)
        loadBrandSettings()
      })
      .catch(() => setError('Kitchen not found'))
  }, [slug, fixedKitchenId])

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
