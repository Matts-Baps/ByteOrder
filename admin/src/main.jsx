import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ClerkProvider } from '@clerk/clerk-react'
import App from './App'
import './index.css'

// Publishable key is fetched at runtime from the server so the same Docker
// image works across environments without a rebuild.
fetch('/api/config')
  .then(async r => {
    if (!r.ok) throw new Error(`Failed to load runtime config (${r.status})`)
    return r.json()
  })
  .then(({ clerkPublishableKey }) => {
    if (!clerkPublishableKey) throw new Error('Missing Clerk publishable key in config response')
    ReactDOM.createRoot(document.getElementById('root')).render(
      <React.StrictMode>
        <ClerkProvider publishableKey={clerkPublishableKey}>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </ClerkProvider>
      </React.StrictMode>
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
