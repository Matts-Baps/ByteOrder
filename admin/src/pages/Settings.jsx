import { useState, useEffect, useRef } from 'react'
import api from '../lib/api'
import axios from 'axios'

const MAX_LOGO_BYTES = 512 * 1024  // 512 KB

export default function Settings() {
  const [printerUrl, setPrinterUrl] = useState('')
  const [kitchenName, setKitchenName] = useState('')
  const [frontendUrl, setFrontendUrl] = useState('')
  const [logo, setLogo] = useState('')          // data URL or ''
  const [currentPw, setCurrentPw] = useState('')
  const [newPw, setNewPw] = useState('')
  const [saved, setSaved] = useState('')
  const [error, setError] = useState('')
  const fileInputRef = useRef(null)

  useEffect(() => {
    api.get('/settings/').then(({ data }) => {
      const map = Object.fromEntries(data.map(s => [s.key, s.value || '']))
      setPrinterUrl(map.printer_url || '')
      setKitchenName(map.kitchen_name || '')
      setFrontendUrl(map.frontend_url || '')
      setLogo(map.logo || '')
    })
  }, [])

  function handleLogoFile(e) {
    const file = e.target.files[0]
    if (!file) return
    if (file.size > MAX_LOGO_BYTES) {
      setError(`Logo must be under 512 KB (this file is ${Math.round(file.size / 1024)} KB)`)
      e.target.value = ''
      return
    }
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
        api.put('/settings/printer_url', { value: printerUrl }),
        api.put('/settings/kitchen_name', { value: kitchenName }),
        api.put('/settings/frontend_url', { value: frontendUrl }),
        api.put('/settings/logo', { value: logo }),
      ])
      setSaved('Settings saved.')
    } catch {
      setError('Failed to save settings.')
    }
  }

  async function changePassword(e) {
    e.preventDefault()
    setError('')
    setSaved('')
    try {
      await axios.post('/api/auth/change-password', {
        current_password: currentPw,
        new_password: newPw,
      }, { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } })
      setSaved('Password updated.')
      setCurrentPw('')
      setNewPw('')
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to change password.')
    }
  }

  return (
    <div className="max-w-lg space-y-8">
      <h1 className="text-2xl font-bold text-gray-900">Settings</h1>

      {saved && <p className="text-green-600 text-sm">{saved}</p>}
      {error && <p className="text-red-600 text-sm">{error}</p>}

      <form onSubmit={saveSettings} className="bg-white rounded-xl shadow p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-800">Kitchen Settings</h2>

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
          <label className="block text-sm font-medium text-gray-700 mb-1">Frontend URL</label>
          <input
            value={frontendUrl}
            onChange={e => setFrontendUrl(e.target.value)}
            className="w-full border rounded-lg px-3 py-2 font-mono text-sm"
            placeholder="http://192.168.1.x:3000"
          />
          <p className="text-xs text-gray-400 mt-1">Used to generate the QR code for customers</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Kitchen Logo</label>
          {logo ? (
            <div className="flex items-center gap-4 mb-2">
              <img src={logo} alt="Logo preview" className="h-16 w-auto object-contain rounded border" />
              <button type="button" onClick={clearLogo} className="text-xs text-red-500 hover:text-red-700">
                Remove
              </button>
            </div>
          ) : (
            <p className="text-xs text-gray-400 mb-2">No logo set — kitchen name will be shown instead</p>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleLogoFile}
            className="text-sm text-gray-600 file:mr-3 file:py-1 file:px-3 file:rounded file:border-0 file:text-sm file:bg-orange-50 file:text-orange-700 hover:file:bg-orange-100"
          />
          <p className="text-xs text-gray-400 mt-1">PNG, JPG or SVG · max 512 KB</p>
        </div>

        <button type="submit" className="bg-orange-600 hover:bg-orange-700 text-white font-medium rounded-lg px-6 py-2">
          Save Settings
        </button>
      </form>

      <form onSubmit={changePassword} className="bg-white rounded-xl shadow p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-800">Change Password</h2>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Current password</label>
          <input
            type="password"
            value={currentPw}
            onChange={e => setCurrentPw(e.target.value)}
            className="w-full border rounded-lg px-3 py-2"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">New password</label>
          <input
            type="password"
            value={newPw}
            onChange={e => setNewPw(e.target.value)}
            className="w-full border rounded-lg px-3 py-2"
            required
            minLength={8}
          />
        </div>
        <button type="submit" className="bg-gray-800 hover:bg-gray-900 text-white font-medium rounded-lg px-6 py-2">
          Change Password
        </button>
      </form>
    </div>
  )
}
