// Regression test: in self-hosted mode the very first API requests a page makes
// must already carry the login token. React runs child effects before parent
// effects, so installing the token interceptor in the layout's useEffect was too
// late and the first requests got 401s.
//
// Uses the real API client; only the network adapter is replaced.
import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import api from './lib/api'
import App from './App'

const requests = []

beforeEach(() => {
  requests.length = 0
  localStorage.clear()
  api.defaults.adapter = async (config) => {
    requests.push({ url: config.url, auth: config.headers?.Authorization })
    const data = config.url === '/settings/' ? [] : { value: null, slug: 'default' }
    return { data, status: 200, statusText: 'OK', headers: {}, config }
  }
})

describe('self-hosted API auth', () => {
  it('sends the token on the first requests after a page load', async () => {
    localStorage.setItem('token', 'test-token')
    render(
      <MemoryRouter initialEntries={['/settings']}>
        <App authMode="self-hosted" />
      </MemoryRouter>
    )
    await screen.findByRole('heading', { name: 'Settings' })

    expect(requests.length).toBeGreaterThan(3)
    expect(requests.filter(r => r.auth !== 'Bearer test-token')).toEqual([])
  })
})
