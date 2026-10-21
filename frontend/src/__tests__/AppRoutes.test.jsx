// Routing tests (#59). Pages are replaced with markers so these tests only check
// which page each URL reaches, in both self-hosted (direct) and slug modes.
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, useParams } from 'react-router-dom'

vi.mock('../contexts/KitchenContext', () => ({
  KitchenProvider: ({ children, fixedKitchenId }) => (
    <div data-testid="kitchen" data-mode={fixedKitchenId ? 'direct' : 'slug'}>{children}</div>
  ),
}))
vi.mock('../pages/Home', () => ({ default: () => <p>home page</p> }))
vi.mock('../pages/Order', () => ({ default: () => <p>order page</p> }))
vi.mock('../pages/TrackOrder', () => ({
  default: function TrackOrder() {
    const { publicId } = useParams()
    return <p>track page {publicId ?? 'lookup'}</p>
  },
}))

import App from '../App'

function renderAt(path) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>
  )
}

describe.each([
  ['self-hosted', '', 'direct'],
  ['slug', '/k/joes', 'slug'],
])('%s routes', (_name, prefix, mode) => {
  it('shows Home at the root', () => {
    renderAt(`${prefix}/`)
    expect(screen.getByText('home page')).toBeInTheDocument()
    expect(screen.getByTestId('kitchen').dataset.mode).toBe(mode)
  })

  it('shows the ordering screen at /order', () => {
    renderAt(`${prefix}/order`)
    expect(screen.getByText('order page')).toBeInTheDocument()
  })

  it('shows the tracking lookup at /track', () => {
    renderAt(`${prefix}/track`)
    expect(screen.getByText('track page lookup')).toBeInTheDocument()
  })

  it('shows a tracked order at /track/:publicId', () => {
    renderAt(`${prefix}/track/abc123`)
    expect(screen.getByText('track page abc123')).toBeInTheDocument()
  })
})

describe('unknown routes', () => {
  it('shows the welcome page', () => {
    renderAt('/unknown-route-xyz')
    expect(screen.getByText('Welcome to ByteOrder')).toBeInTheDocument()
  })
})
