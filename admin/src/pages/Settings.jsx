import { useState, useEffect, useRef } from 'react'
import { useOrganization } from '@clerk/clerk-react'
import api from '../lib/api'

const MAX_LOGO_BYTES = 512 * 1024  // 512 KB

export default function Settings() {
  const { organization } = useOrganization()

  const [printerUrl, setPrinterUrl] = useState('')
  const [kitchenName, setKitchenName] = useState('')
  const [logo, setLogo] = useState('')
  const [brandPrimary, setBrandPrimary] = useState('#ea580c')
  const [brandBg, setBrandBg] = useState('#f9fafb')
  const [brandSurface, setBrandSurface] = useState('#ffffff')
  const [brandText, setBrandText] = useState('#111827')
  const [slug, setSlug] = useState('')
  const [slugBanner, setSlugBanner] = useState(false)
  const [saved, setSaved] = useState('')
  const [error, setError] = useState('')
  const fileInputRef = useRef(null)

  useEffect(() => {
    api.get('/settings/').then(({ data }) => {
      const map = Object.fromEntries(data.map(s => [s.key, s.value || '']))
      setPrinterUrl(map.printer_url || '')
      setKitchenName(map.kitchen_name || '')
      setLogo(map.logo || '')
      const colour = map.brand_primary || '#ea580c'
      setBrandPrimary(colour)
      document.documentElement.style.setProperty('--brand-primary', colour)
      const bg = map.brand_bg || '#f9fafb'
      setBrandBg(bg)
      document.documentElement.style.setProperty('--brand-bg', bg)
      const surface = map.brand_surface || '#ffffff'
      setBrandSurface(surface)
      document.documentElement.style.setProperty('--brand-surface', surface)
      const text = map.brand_text || '#111827'
      setBrandText(text)
      document.documentElement.style.setProperty('--brand-text', text)
    })

    api.get('/menu/kitchens/me')
      .then(({ data }) => setSlug(data.slug))
      .catch(err => {
        // 404 = not set up yet — pre-fill from Clerk org slug
        if (err.response?.status === 404 && organization?.slug) {
          setSlug(organization.slug)
          setSlugBanner(true)
        }
      })
  }, [organization])

  function handleBrandColour(hex) {
    setBrandPrimary(hex)
    document.documentElement.style.setProperty('--brand-primary', hex)
  }
  function handleBrandBg(hex) {
    setBrandBg(hex)
    document.documentElement.style.setProperty('--brand-bg', hex)
  }
  function handleBrandSurface(hex) {
    setBrandSurface(hex)
    document.documentElement.style.setProperty('--brand-surface', hex)
  }
  function handleBrandText(hex) {
    setBrandText(hex)
    document.documentElement.style.setProperty('--brand-text', hex)
  }

  function handleLogoFile(e) {
    const file = e.target.files[0]
    if (!file) return
    if (file.size > MAX_LOGO_BYTES) {
      setError(`Logo must be under 512 KB (this file is ${Math.round(file.size / 1024)} KB)`)
      e.target.value = ''
      return
    }
    setError('')
    const reader = new FileReader()
    reader.onload = ev => setLogo(ev.target.result)
    reader.readAsDataURL(file)
  }

  function clearLogo() {
    setLogo('')
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  async function saveSettings(e) {
    e.preventDefault()
    setError('')
    setSaved('')
    try {
      await Promise.all([
        api.put('/settings/printer_url',   { value: printerUrl }),
        api.put('/settings/kitchen_name',  { value: kitchenName }),
        api.put('/settings/logo',          { value: logo }),
        api.put('/settings/brand_primary', { value: brandPrimary }),
        api.put('/settings/brand_bg',      { value: brandBg }),
        api.put('/settings/brand_surface', { value: brandSurface }),
        api.put('/settings/brand_text',    { value: brandText }),
        api.put('/menu/kitchens/me',       { slug }),
      ])
      setSlugBanner(false)
      setSaved('Settings saved.')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save settings.')
    }
  }

  const customerUrl = slug
    ? `${window.location.origin.replace(/admin\./, '')}/k/${slug}`
    : null

  return (
    <div className="max-w-lg space-y-8">
      <h1 className="text-2xl font-bold text-brand-text">Settings</h1>

      {saved && <p className="text-green-600 text-sm">{saved}</p>}
      {error && <p className="text-red-600 text-sm">{error}</p>}

      <form onSubmit={saveSettings} className="bg-brand-surface rounded-xl shadow p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-800">Kitchen Settings</h2>

        {slugBanner && (
          <div className="bg-blue-50 border border-blue-200 text-blue-800 text-sm rounded-lg px-4 py-3">
            Customer URL pre-filled from your Clerk organization. Review and save to confirm.
            <button type="button" onClick={() => setSlugBanner(false)} className="ml-2 underline text-blue-600 text-xs">Dismiss</button>
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Kitchen Name</label>
          <input
            value={kitchenName}
            onChange={e => setKitchenName(e.target.value)}
            className="w-full border rounded-lg px-3 py-2"
            placeholder="e.g. The Garden Kitchen"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Customer URL slug</label>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-400 shrink-0">/k/</span>
            <input
              value={slug}
              onChange={e => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
              className="flex-1 border rounded-lg px-3 py-2 font-mono text-sm"
              placeholder="my-kitchen"
            />
          </div>
          {customerUrl && (
            <p className="text-xs text-gray-500 mt-1">
              Customer URL:{' '}
              <a href={customerUrl} target="_blank" rel="noopener noreferrer" className="text-brand-600 underline break-all">
                {customerUrl}
              </a>
            </p>
          )}
          <p className="text-xs text-gray-400 mt-1">Lowercase letters, numbers and hyphens only</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Printer URL</label>
          <input
            value={printerUrl}
            onChange={e => setPrinterUrl(e.target.value)}
            className="w-full border rounded-lg px-3 py-2 font-mono text-sm"
            placeholder="http://192.168.1.x:5000"
          />
          <p className="text-xs text-gray-400 mt-1">URL of your ble-printer-server instance</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Brand Colour</label>
          <div className="flex items-center gap-3">
            <input type="color" value={brandPrimary} onChange={e => handleBrandColour(e.target.value)} className="h-10 w-16 rounded border cursor-pointer p-0.5" />
            <span className="text-sm font-mono text-gray-600">{brandPrimary}</span>
            <button type="button" onClick={() => handleBrandColour('#ea580c')} className="text-xs text-gray-400 hover:text-gray-700 underline">Reset</button>
          </div>
          <p className="text-xs text-gray-400 mt-1">Applied across the ordering interface and admin panel — live preview as you pick</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Background Colour</label>
          <div className="flex items-center gap-3">
            <input type="color" value={brandBg} onChange={e => handleBrandBg(e.target.value)} className="h-10 w-16 rounded border cursor-pointer p-0.5" />
            <span className="text-sm font-mono text-gray-600">{brandBg}</span>
            <button type="button" onClick={() => handleBrandBg('#f9fafb')} className="text-xs text-gray-400 hover:text-gray-700 underline">Reset</button>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Surface Colour</label>
          <div className="flex items-center gap-3">
            <input type="color" value={brandSurface} onChange={e => handleBrandSurface(e.target.value)} className="h-10 w-16 rounded border cursor-pointer p-0.5" />
            <span className="text-sm font-mono text-gray-600">{brandSurface}</span>
            <button type="button" onClick={() => handleBrandSurface('#ffffff')} className="text-xs text-gray-400 hover:text-gray-700 underline">Reset</button>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Text Colour</label>
          <div className="flex items-center gap-3">
            <input type="color" value={brandText} onChange={e => handleBrandText(e.target.value)} className="h-10 w-16 rounded border cursor-pointer p-0.5" />
            <span className="text-sm font-mono text-gray-600">{brandText}</span>
            <button type="button" onClick={() => handleBrandText('#111827')} className="text-xs text-gray-400 hover:text-gray-700 underline">Reset</button>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Kitchen Logo</label>
          {logo ? (
            <div className="flex items-center gap-4 mb-2">
              <img src={logo} alt="Logo preview" className="h-16 w-auto object-contain rounded border" />
              <button type="button" onClick={clearLogo} className="text-xs text-red-500 hover:text-red-700">Remove</button>
            </div>
          ) : (
            <p className="text-xs text-gray-400 mb-2">No logo set — kitchen name will be shown instead</p>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleLogoFile}
            className="text-sm text-gray-600 file:mr-3 file:py-1 file:px-3 file:rounded file:border-0 file:text-sm file:bg-brand-50 file:text-brand-700 hover:file:bg-brand-100"
          />
          <p className="text-xs text-gray-400 mt-1">PNG, JPG or SVG · max 512 KB</p>
        </div>

        <button type="submit" className="bg-brand-600 hover:bg-brand-700 text-white font-medium rounded-lg px-6 py-2">
          Save Settings
        </button>
      </form>
    </div>
  )
}
