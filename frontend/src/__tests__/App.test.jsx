import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

// Mock KitchenContext so components don't need a real provider
vi.mock('../contexts/KitchenContext', () => ({
  KitchenProvider: ({ children }) => children,
  useKitchen: () => ({ kitchenId: 'test-kitchen', slug: null }),
}))

// Mock api to prevent real HTTP calls
vi.mock('../lib/api', () => ({
  menuApi: { get: vi.fn(() => Promise.resolve({ data: { value: null } })) },
  orderApi: { get: vi.fn(() => Promise.resolve({ data: [] })), post: vi.fn() },
  setKitchenId: vi.fn(),
}))

// Mock qrcode.react to avoid canvas issues in jsdom
vi.mock('qrcode.react', () => ({
  QRCodeSVG: () => null,
}))

import App from '../App'

describe('App', () => {
  it('renders without crashing at root path', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    )
    // App renders without throwing
    expect(document.body).toBeDefined()
  })

  it('renders 404-style fallback for unknown routes', () => {
    render(
      <MemoryRouter initialEntries={['/unknown-route-xyz']}>
        <App />
      </MemoryRouter>
    )
    expect(screen.getByText(/ByteOrder/i)).toBeDefined()
  })
})
