import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ClerkProvider } from '@clerk/clerk-react'
import App from './App'
import './index.css'

// Publishable key is fetched at runtime from the server so the same Docker
// image works across environments without a rebuild.
fetch('/api/config')
  .then(r => r.json())
  .then(({ clerkPublishableKey }) => {
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
