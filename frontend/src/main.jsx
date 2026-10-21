import { startTelemetry } from './telemetry'

import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

// Start telemetry before rendering, so the API calls made while the page loads
// are recorded too. When telemetry is off this resolves straight away.
startTelemetry().then(() => {
  ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </React.StrictMode>
  )
})
