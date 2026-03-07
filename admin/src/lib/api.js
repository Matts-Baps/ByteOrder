import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use(async config => {
  const token = await window.Clerk?.session?.getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  r => r,
  err => {
    if (err.response?.status === 401) window.location.href = '/'
    return Promise.reject(err)
  }
)

export default api
