import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// Called once by ApiSetup (admin/src/App.jsx) after Clerk has initialised,
// so token retrieval and 401 handling go through Clerk's React APIs.
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

export default api
