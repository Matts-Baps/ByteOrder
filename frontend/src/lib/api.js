import axios from 'axios'

export const menuApi = axios.create({ baseURL: '/api' })
export const orderApi = axios.create({ baseURL: '/orders-api' })

export function setKitchenId(id) {
  menuApi.defaults.headers.common['X-Kitchen-ID'] = id
  orderApi.defaults.headers.common['X-Kitchen-ID'] = id
}
