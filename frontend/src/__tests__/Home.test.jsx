import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

vi.mock('../contexts/KitchenContext', () => ({
  KitchenProvider: ({ children }) => children,
  useKitchen: () => ({ kitchenId: 'test-kitchen', slug: null }),
}))

vi.mock('../lib/api', () => ({
  menuApi: {
    get: vi.fn((path) => {
      if (path.includes('kitchen_name')) return Promise.resolve({ data: { value: 'Test Kitchen' } })
      if (path.includes('logo')) return Promise.resolve({ data: { value: null } })
      if (path.includes('brand_primary')) return Promise.resolve({ data: { value: '#ea580c' } })
      return Promise.resolve({ data: {} })
    }),
  },
  orderApi: {
    get: vi.fn(() => Promise.resolve({ data: [] })),
  },
  setKitchenId: vi.fn(),
}))

vi.mock('qrcode.react', () => ({
  QRCodeSVG: ({ value }) => <div data-testid="qr-code">{value}</div>,
}))

import Home from '../pages/Home'

describe('Home', () => {
  it('renders without crashing', () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    )
    expect(document.body).toBeDefined()
  })

  it('shows Place Order link', () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    )
    expect(screen.getByText('Place Order')).toBeDefined()
  })

  it('shows Track Order link', () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    )
    expect(screen.getByText('Track Order')).toBeDefined()
  })

  it('shows empty queue message when no orders', () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    )
    expect(screen.getByText(/No active orders/i)).toBeDefined()
  })
})
