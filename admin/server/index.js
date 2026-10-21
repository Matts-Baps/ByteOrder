// OpenTelemetry — must start before anything else is required
require('./telemetry').startTelemetry()

const app = require('./app')

const PORT = process.env.PORT || 3001
app.listen(PORT, () => console.log(`Admin server running on :${PORT} (auth: ${process.env.AUTH_MODE || 'cloud'})`))
