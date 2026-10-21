import axios from 'axios'

export const menuApi = axios.create({ baseURL: '/api' })
export const orderApi = axios.create({ baseURL: '/orders-api' })
// Model replies can take a while on a busy GPU.
export const assistantApi = axios.create({ baseURL: '/assistant-api', timeout: 120000 })

export function setKitchenId(id) {
  menuApi.defaults.headers.common['X-Kitchen-ID'] = id
  orderApi.defaults.headers.common['X-Kitchen-ID'] = id
  assistantApi.defaults.headers.common['X-Kitchen-ID'] = id
}
