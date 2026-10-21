# How the ordering assistant works

The assistant lives in `assistant-service`, a FastAPI service. Customers open it with **Ask for help** on the ordering page, describe what they want, and get back a suggested order. They press **Use this order** to move it into their basket, check it, and place it as normal.

## Request flow

1. The browser sends the whole conversation so far to `POST /assistant-api/chat`. The service keeps no conversation state.
2. The service checks the rate limits, then loads the kitchen's active menu and name from menu-service.
3. It builds a system prompt containing the rules, the customer's name and a compact text version of the menu.
4. It runs the **agent loop**:
    1. Send the messages and the tool definition to the model.
    2. If the model replies with text, that is the answer. Stop.
    3. If the model calls a tool, run it, add the result to the messages, and go back to step 1.
5. It returns the reply and, if the model saved one, the draft order.

The loop runs at most `MAX_STEPS` times (default 4). If it runs out, or the model returns an empty reply, the customer gets a fallback message pointing them back to the menu.

## The tool

There is one tool, `propose_order`. The model passes item ids from the menu, with optional quantity and toppings to `remove` or `add`.

The tool checks the proposal against the menu:

- the item exists and is active
- each topping named is linked to that item
- the order has between 1 and 10 items

If anything is wrong, the errors go back to the model so it can try again. If it is valid, the tool builds basket items in the same shape the ordering page sends to order-service, and the service returns them as the draft.

Toppings follow the ordering page: every ingredient linked to an item can be switched on or off, and its "default" flag decides whether it starts on. Option groups are ignored, as the ordering page does not use them yet.

## Guardrails

| Risk | What stops it |
|---|---|
| The model places an unwanted order | It cannot. The tool only builds a draft; the customer places the order. |
| The model invents items | The tool rejects unknown item ids and toppings. |
| A client injects system or tool messages | The API only accepts `user` and `assistant` messages, and the last one must be from the customer. |
| Instructions hidden in the customer's name | The name is flattened to one line, quotes are removed, and it is cut to 60 characters. The prompt says to treat it as information. |
| A client forges earlier assistant replies | Possible, as the conversation is stored in the browser. The draft is still checked against the menu, and a customer can already send any order directly to order-service, so this gains nothing. |
| GPU overload | Fixed-window limits in Redis: per client (from `X-Forwarded-For`, so best effort) and per kitchen (a hard ceiling). |
| Runaway generation | Each model reply is capped at `OLLAMA_MAX_OUTPUT_TOKENS` (default 512). Each conversation is capped at 20 messages of up to 1,000 characters. |
| Allergy advice | The menu shows each topping's allergens, or "not confirmed" ([#55](https://github.com/Matts-Baps/ByteOrder/issues/55)), and the prompt says to repeat only that and never call anything "safe". The prompt cannot guarantee this, which is what the [allergen eval](evals.md#3-allergen-claims-match-the-menu-data) checks. |
| A draft with something the customer is allergic to | `propose_order` takes `avoid_allergens`. If it is set, the draft is rejected (`error.type=allergen_conflict`) when any included topping contains one of those allergens or is unchecked, or when an item has no ingredients listed. This only works if the model passes the allergy on. |

!!! note "The prompt is not a security boundary"
    Rules in the system prompt make good behaviour likely, not certain. A small model in particular can be talked out of them (see the [scenario results](scenarios.md#baseline-results)). Anything that must never happen is enforced in code instead.

## Malformed tool calls

When the model writes tool-call JSON that Ollama cannot parse, Ollama answers with HTTP 500 and an `invalid tool call arguments` error. The service treats this as a failed step and tries again, rather than giving up. Each failure is recorded as a `chat` span with `error.type=invalid_tool_call`.

## Configuration

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_URL` | `http://ollama:11434` | Ollama server |
| `OLLAMA_MODEL` | `qwen3:4b-instruct` | Must support tool calling (`ollama show <model>` lists `tools` under capabilities) |
| `OLLAMA_NUM_CTX` | unset | Context window. Unset uses the server's setting. Changing it makes Ollama reload the model. |
| `OLLAMA_MAX_OUTPUT_TOKENS` | `512` | Cap on each model reply |
| `OLLAMA_TEMPERATURE` | unset | Unset uses the model's default |
| `OLLAMA_TIMEOUT_SECONDS` | `60` | Per model call |
| `MENU_SERVICE_URL` | `http://menu-service:8000` | |
| `REDIS_URL` | `redis://redis:6379` | |
| `AUTH_MODE` | `cloud` | In `self-hosted` mode `DEFAULT_KITCHEN_ID` is always used |
| `MAX_STEPS` | `4` | Model calls per customer message |
| `RATE_LIMIT_PER_CLIENT_PER_MINUTE` | `10` | |
| `RATE_LIMIT_PER_KITCHEN_PER_MINUTE` | `60` | |
| `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` | `false` | Record prompts and replies on spans. See [Telemetry](telemetry.md). |

In Helm, set `assistant.enabled: true` and `assistant.ollamaUrl`. The frontend only shows **Ask for help** when `/assistant-api/health` responds, so the feature disappears cleanly when it is not deployed.
