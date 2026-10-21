import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'

// Mock axios before importing the module under test
vi.mock('axios', () => {
  const mockInstance = {
    get: vi.fn(),
    post: vi.fn(),
    defaults: { headers: { common: {} } },
  }
  return {
    default: {
      create: vi.fn(() => mockInstance),
    },
  }
})

describe('api.js', () => {
  it('creates menuApi and orderApi with axios.create', async () => {
    const { menuApi, orderApi } = await import('../lib/api.js')
    expect(menuApi).toBeDefined()
    expect(orderApi).toBeDefined()
  })

  it('setKitchenId sets X-Kitchen-ID header on all instances', async () => {
    const { menuApi, orderApi, assistantApi, setKitchenId } = await import('../lib/api.js')
    setKitchenId('kitchen-123')
    expect(menuApi.defaults.headers.common['X-Kitchen-ID']).toBe('kitchen-123')
    expect(orderApi.defaults.headers.common['X-Kitchen-ID']).toBe('kitchen-123')
    expect(assistantApi.defaults.headers.common['X-Kitchen-ID']).toBe('kitchen-123')
  })

  it('creates assistantApi pointing at the assistant proxy', async () => {
    await import('../lib/api.js')
    expect(axios.create).toHaveBeenCalledWith(expect.objectContaining({ baseURL: '/assistant-api' }))
  })
})
