import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

// Runtime config is fetched so the same Docker image works in both
// self-hosted and cloud modes without a rebuild.
fetch('/api/config')
  .then(async r => {
    if (!r.ok) throw new Error(`Failed to load runtime config (${r.status})`)
    return r.json()
  })
  .then(async ({ authMode, clerkPublishableKey }) => {
    let tree

    if (authMode === 'cloud') {
      const { ClerkProvider } = await import('@clerk/clerk-react')
      tree = (
        <ClerkProvider publishableKey={clerkPublishableKey}>
          <BrowserRouter>
            <App authMode="cloud" />
          </BrowserRouter>
        </ClerkProvider>
      )
    } else {
      tree = (
        <BrowserRouter>
          <App authMode="self-hosted" />
        </BrowserRouter>
      )
    }

    ReactDOM.createRoot(document.getElementById('root')).render(
      <React.StrictMode>{tree}</React.StrictMode>
    )
  })
  .catch(err => {
    console.error(err)
    ReactDOM.createRoot(document.getElementById('root')).render(
      <React.StrictMode>
        <div role="alert" style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
          Failed to load admin configuration. Please try again or contact support.
        </div>
      </React.StrictMode>
    )
  })
