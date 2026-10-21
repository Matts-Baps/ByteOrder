import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

const clerkSignOut = vi.fn()
vi.mock('@clerk/clerk-react', () => ({
  useClerk: () => ({ signOut: clerkSignOut }),
  useOrganization: () => ({ organization: { name: 'Clerk Kitchen', slug: 'clerk-kitchen' } }),
}))

import { CloudAuthProvider, SelfHostedAuthProvider, useAdminAuth } from './auth'

function Probe() {
  const { mode, organization, signOut } = useAdminAuth()
  return (
    <div>
      <p>mode: {mode}</p>
      <p>org: {organization?.name ?? 'none'}</p>
      <button onClick={signOut}>Sign out</button>
    </div>
  )
}

describe('useAdminAuth', () => {
  beforeEach(() => {
    localStorage.clear()
    clerkSignOut.mockClear()
  })

  it('throws a clear error outside a provider', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => render(<Probe />)).toThrow(/useAdminAuth must be used inside/)
    console.error.mockRestore()
  })

  it('self-hosted: no organization, sign out clears the token and goes to /login', async () => {
    localStorage.setItem('token', 'abc')
    render(
      <MemoryRouter initialEntries={['/orders']}>
        <Routes>
          <Route path="/login" element={<p>login page</p>} />
          <Route path="/orders" element={<SelfHostedAuthProvider><Probe /></SelfHostedAuthProvider>} />
        </Routes>
      </MemoryRouter>
    )
    expect(screen.getByText('mode: self-hosted')).toBeInTheDocument()
    expect(screen.getByText('org: none')).toBeInTheDocument()

    await userEvent.setup().click(screen.getByRole('button', { name: 'Sign out' }))
    expect(localStorage.getItem('token')).toBeNull()
    expect(screen.getByText('login page')).toBeInTheDocument()
  })

  it('cloud: uses the Clerk organization and Clerk sign out', async () => {
    render(<CloudAuthProvider><Probe /></CloudAuthProvider>)
    expect(screen.getByText('mode: cloud')).toBeInTheDocument()
    expect(screen.getByText('org: Clerk Kitchen')).toBeInTheDocument()

    await userEvent.setup().click(screen.getByRole('button', { name: 'Sign out' }))
    expect(clerkSignOut).toHaveBeenCalled()
  })
})

describe('Clerk usage', () => {
  // Clerk hooks crash outside <ClerkProvider>, i.e. in self-hosted mode (#54).
  // Only these files may import Clerk; everything else must use useAdminAuth().
  const ALLOWED = ['../main.jsx', '../App.jsx', './auth.jsx']

  it('is limited to the cloud-only entry points', () => {
    const sources = import.meta.glob(['../**/*.jsx', '!../**/*.test.jsx'], { query: '?raw', import: 'default', eager: true })
    const offenders = Object.entries(sources)
      .filter(([path, code]) => !ALLOWED.includes(path) && code.includes('@clerk/clerk-react'))
      .map(([path]) => path)
    expect(Object.keys(sources).length).toBeGreaterThan(5)
    expect(offenders).toEqual([])
  })
})
