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
export function setupSelfHostedInterceptors() {
  const requestId = api.interceptors.request.use(config => {
    const token = localStorage.getItem('token')
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
  })

  const responseId = api.interceptors.response.use(
    r => r,
    err => {
      if (err.response?.status === 401) {
        localStorage.removeItem('token')
        window.location.href = '/login'
      }
      return Promise.reject(err)
    }
  )

  return () => {
    api.interceptors.request.eject(requestId)
    api.interceptors.response.eject(responseId)
  }
}

export default api
