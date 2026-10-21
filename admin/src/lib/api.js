import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// ── Cloud mode: called by ApiSetup after Clerk has initialised ────────────────
export function setupApiInterceptors({ getToken, openSignIn }) {
  const requestId = api.interceptors.request.use(async config => {
    const token = await getToken()
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
  })

  const responseId = api.interceptors.response.use(
    r => r,
    err => {
      if (err.response?.status === 401) openSignIn()
      return Promise.reject(err)
    }
  )

  return () => {
    api.interceptors.request.eject(requestId)
    api.interceptors.response.eject(responseId)
  }
}

// ── Self-hosted mode: plain localStorage JWT ──────────────────────────────────
// Installed once for the life of the page. It must be in place before any page
// component mounts, so it is called during render rather than in an effect.
let selfHostedInstalled = false

export function setupSelfHostedInterceptors() {
  if (selfHostedInstalled) return
  selfHostedInstalled = true

  api.interceptors.request.use(config => {
    const token = localStorage.getItem('token')
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
  })

  api.interceptors.response.use(
    r => r,
    err => {
      if (err.response?.status === 401) {
        localStorage.removeItem('token')
        window.location.href = '/login'
      }
      return Promise.reject(err)
    }
  )
}

export default api
