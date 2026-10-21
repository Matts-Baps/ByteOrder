"""Convert chat messages to the OpenTelemetry GenAI semantic convention formats.

The conventions describe messages as a list of {role, parts}. Span attributes
cannot hold nested structures, so each value is recorded as a JSON string.
See https://opentelemetry.io/docs/specs/semconv/gen-ai/
"""
import json

from app.llm import LLMResponse


def _dump(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def system_instructions(messages: list[dict]) -> str | None:
    parts = [{"type": "text", "content": m["content"]} for m in messages if m["role"] == "system"]
    return _dump(parts) if parts else None


def _parts(message: dict) -> list[dict]:
    if message["role"] == "tool":
        return [
            {
                "type": "tool_call_response",
                "id": message.get("tool_call_id"),
                "response": message.get("content", ""),
            }
        ]
    parts = []
    if message.get("content"):
        parts.append({"type": "text", "content": message["content"]})
    for call in message.get("tool_calls") or []:
        fn = call.get("function", {})
        parts.append(
            {
                "type": "tool_call",
                "id": call.get("id"),
                "name": fn.get("name"),
                "arguments": fn.get("arguments"),
            }
        )
    return parts


def input_messages(messages: list[dict]) -> str:
    return _dump([{"role": m["role"], "parts": _parts(m)} for m in messages if m["role"] != "system"])


def output_messages(response: LLMResponse) -> str:
    parts = []
    if response.content:
        parts.append({"type": "text", "content": response.content})
    for call in response.tool_calls:
        parts.append({"type": "tool_call", "id": call.id, "name": call.name, "arguments": call.arguments})
    return _dump([{"role": "assistant", "parts": parts, "finish_reason": response.finish_reason or "stop"}])


def text_output(text: str) -> str:
    return _dump([{"role": "assistant", "parts": [{"type": "text", "content": text}], "finish_reason": "stop"}])
