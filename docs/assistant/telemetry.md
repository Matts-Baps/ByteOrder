# Telemetry

The assistant is traced by hand following the [OpenTelemetry GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/), rather than with an instrumentation library, so every attribute is visible in `app/agent.py`.

OpenTelemetry is configured only through the standard `OTEL_*` variables, and export is enabled only when `OTEL_EXPORTER_OTLP_ENDPOINT` is set. `OTEL_EXPORTER_OTLP_PROTOCOL` may be `http/protobuf` (default) or `grpc`. If another component, such as the Dash0 operator, has already set up tracing, the service uses that instead of adding its own.

## Spans

Each customer message produces this tree, under the FastAPI request span:

```
POST /chat
└── invoke_agent byteorder-assistant
    ├── GET  (menu-service: categories and kitchen name)
    ├── chat qwen3:4b-instruct
    ├── execute_tool propose_order
    └── chat qwen3:4b-instruct
```

### `invoke_agent byteorder-assistant`

One per customer message. This is the span to run conversation-level evals on.

| Attribute | Notes |
|---|---|
| `gen_ai.operation.name` | `invoke_agent` |
| `gen_ai.agent.name` | `byteorder-assistant` |
| `gen_ai.provider.name` | `ollama` |
| `gen_ai.request.model` | |
| `gen_ai.conversation.id` | Set by the browser, the same for every message in one chat |
| `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens` | Totals across all model calls |
| `gen_ai.system_instructions` | Content capture only. Includes the menu. |
| `gen_ai.input.messages` | Content capture only. The conversation as the customer sees it (no tool messages). |
| `gen_ai.output.messages` | Content capture only. The final reply. |
| `byteorder.kitchen_id` | |
| `byteorder.assistant.steps` | Model calls made |
| `byteorder.assistant.step_limit_reached` | `true` if the loop gave up |
| `byteorder.assistant.invalid_tool_calls` | Malformed tool calls that were retried |
| `byteorder.assistant.draft_items` | Items in the draft returned to the customer (0 for none) |
| `error.type` | Set if the model server failed |

### `chat <model>`

One per model call (span kind `CLIENT`). Carries `gen_ai.operation.name=chat`, provider, request and response model, `server.address`, `server.port`, `gen_ai.response.finish_reasons`, token usage and, with content capture, the full input and output messages including tool calls. `error.type` is `invalid_tool_call` or the exception name on failure.

### `execute_tool propose_order`

One per tool call. Carries `gen_ai.operation.name=execute_tool`, `gen_ai.tool.name`, `gen_ai.tool.call.id`, `gen_ai.tool.type=function` and, with content capture, `gen_ai.tool.call.arguments` and `gen_ai.tool.call.result`. A rejected proposal sets `error.type=invalid_order`.

## Metrics

| Metric | Type | Attributes |
|---|---|---|
| `gen_ai.client.token.usage` | Histogram, `{token}` | `gen_ai.token.type` (`input`/`output`), operation, provider, model |
| `gen_ai.client.operation.duration` | Histogram, `s` | operation, provider, model, `error.type` on failure |
| `byteorder.assistant.rate_limited` | Counter | |

## Content capture

Message content is off by default. Set `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true` (Helm: `assistant.captureMessageContent: true`) to record prompts, replies and tool arguments.

Evals that judge what was said need this. Turning it on means **customer messages and names are stored in your telemetry backend**, so check that fits your privacy obligations. Dash0 can also [redact GenAI attributes on ingestion](https://www.dash0.com/docs/dash0/darkplane/insights/data-privacy#redact-on-ingestion), but evals skip spans whose referenced attributes were redacted.
