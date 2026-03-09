// OpenTelemetry — must be required before anything else
if (process.env.OTEL_ENDPOINT) {
  require('./telemetry')
}

const app = require('./app')

const PORT = process.env.PORT || 3001
app.listen(PORT, () => console.log(`Admin server running on :${PORT} (auth: ${process.env.AUTH_MODE || 'cloud'})`))
