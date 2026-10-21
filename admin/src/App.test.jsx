// Regression tests for #54: the admin UI must work in self-hosted mode,
// where there is no ClerkProvider. @clerk/clerk-react is deliberately NOT
// mocked here, so any Clerk hook used outside cloud mode throws and fails.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

vi.mock('./lib/api', () => ({
  default: {
    get: vi.fn((url) => {
      if (url === '/settings/') return Promise.resolve({ data: [] })
      if (url === '/menu/kitchens/me') return Promise.resolve({ data: { kitchen_id: 'default', slug: 'default' } })
      return Promise.resolve({ data: { value: null } })
    }),
    put: vi.fn(() => Promise.resolve({ data: {} })),
  },
  setupApiInterceptors: vi.fn(() => () => {}),
  setupSelfHostedInterceptors: vi.fn(() => () => {}),
}))

import App from './App'

function renderApp(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App authMode="self-hosted" />
    </MemoryRouter>
  )
}

describe('App in self-hosted mode', () => {
  beforeEach(() => localStorage.clear())

  it('shows the login page when there is no token', () => {
    renderApp('/settings')
    expect(screen.getByText('Admin sign in')).toBeInTheDocument()
  })

  it('renders the admin layout and Settings page without Clerk', async () => {
    localStorage.setItem('token', 'test-token')
    renderApp('/settings')
    expect(screen.getByText('ByteOrder Admin')).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Settings' })).toBeInTheDocument()
    expect(screen.queryByText(/pre-filled from your Clerk organization/i)).not.toBeInTheDocument()
  })

  it('logs out by clearing the token and returning to the login page', async () => {
    localStorage.setItem('token', 'test-token')
    renderApp('/settings')
    await userEvent.setup().click(screen.getByRole('button', { name: 'Log out' }))
    expect(localStorage.getItem('token')).toBeNull()
    expect(screen.getByText('Admin sign in')).toBeInTheDocument()
  })
})
