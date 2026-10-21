# Browser telemetry

The customer frontend can send browser telemetry to an OpenTelemetry collector using the [Dash0 Web SDK](https://dash0.com/docs/dash0/miscellaneous/tooling/web-sdk/overview). It is off by default.

The SDK records page views, navigation timing, Core Web Vitals, JavaScript errors, rage clicks, and `fetch`/`XMLHttpRequest` calls. Session replay is optional and off by default.

## How it works

1. When the frontend container starts, `/docker-entrypoint.d/40-byteorder-browser-telemetry.sh` writes `/runtime-config.js`. The page loads it before the app, and it tells the app whether to start the SDK.
2. When telemetry is on, the same script writes nginx rules that forward `POST /otel/v1/traces` and `POST /otel/v1/logs` to `OTEL_EXPORTER_OTLP_ENDPOINT`.
3. The SDK sends to `/otel` on the frontend's own site, so no CORS setup is needed. Requests to ByteOrder's own APIs carry trace context, which links browser activity to backend traces.

The SDK requires a token, so the browser sends a placeholder. nginx removes it, and the browser's cookies, before forwarding. If `OTEL_EXPORTER_OTLP_HEADERS` is set, nginx adds those headers instead, so credentials stay on the server.

## Configuration

| Docker Compose | Helm | Default | Meaning |
|---|---|---|---|
| `BROWSER_TELEMETRY_ENABLED` | `otel.browser.enabled` | `false` | Switch browser telemetry on |
| `BROWSER_TELEMETRY_SAMPLE_RATE` | `otel.browser.sampleRate` | `100` | Percentage of browser sessions to record (0–100) |
| `BROWSER_TELEMETRY_SESSION_REPLAY` | `otel.browser.sessionReplay` | `false` | Record sessions for replay in Dash0 |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `otel.endpoint` | — | Collector to forward to. Must accept OTLP over HTTP (usually port 4318) |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `otel.protocol` | `http/protobuf` | Must be an HTTP protocol; `grpc` leaves browser telemetry off |
| `OTEL_EXPORTER_OTLP_HEADERS` | `otel.headersSecret` | — | Headers nginx adds when forwarding, e.g. an auth token |
| `OTEL_SERVICE_NAME` | — | `byteorder-frontend` | Service name for browser telemetry |

The Helm chart refuses to render with `otel.browser.enabled=true` and no `otel.endpoint`.

If the settings are wrong (no endpoint, a gRPC protocol, a collector name that doesn't resolve, an invalid sample rate or header), the script leaves browser telemetry off and logs a line starting `byteorder-browser-telemetry:` explaining why. nginx still starts and serves the app.

## Session replay

With session replay on, the SDK records the page with [rrweb](https://github.com/rrweb-io/rrweb) and sends it to Dash0 alongside the other telemetry, through the same `/otel/v1/logs` path. The recorder is only downloaded when replay is on.

Everything typed into inputs, such as guests' names and chat messages, is replaced with asterisks before it leaves the browser. Text shown on the page is recorded as is, including the assistant's replies and the messages in the chat history. Mark an element with the `dash0-mask` class to mask its text, or `dash0-block` to leave it out of the recording.

## Limits on the public endpoint

Anyone who can load the ordering page can post to `/otel`. To limit what that can cost:

- Only `POST` to the two paths above is forwarded.
- Request bodies are limited to 1 MB. Dash0 notes the SDK sends batches of up to about 512 KB ([Proxy the Ingestion Endpoint](https://dash0.com/docs/dash0/monitoring/websites/proxying-the-ingestion-endpoint)).
- nginx allows 20 requests per second per client address, with a burst of 40. Behind an ingress, every browser arrives from the ingress's address, so this becomes one shared limit for all browsers.

## Known limitation

When nginx sits behind an ingress and forwards to a collector, the collector sees nginx as the sender. Dash0 works out a session's location from the client IP, so unless the collector passes on `X-Forwarded-For` (see the Dash0 page above), sessions show the cluster's location.
