"""Minimal client for Ollama's native chat API.

The native API (rather than Ollama's OpenAI-compatible one) is used because it
lets us set the context window size per request.
"""
import json
import uuid
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import urlsplit

import httpx


class LLMUnavailable(Exception):
    """The model server could not be reached or returned an error."""


class InvalidToolCall(Exception):
    """The model produced a tool call Ollama could not parse. Retrying usually works."""


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class LLMResponse:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str | None = None
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


class ChatModel(Protocol):
    provider: str
    model: str
    server_address: str | None
    server_port: int | None

    async def chat(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        """Send the conversation and tool definitions; return the model's reply."""


class OllamaChat:
    provider = "ollama"

    def __init__(
        self,
        base_url: str,
        model: str,
        num_ctx: int | None = None,
        timeout: float = 90.0,
        max_output_tokens: int | None = 512,
        temperature: float | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_output_tokens = max_output_tokens
        self.temperature = temperature
        # Ollama's option names. Unset values fall back to the model's defaults.
        options = {"num_ctx": num_ctx, "num_predict": max_output_tokens, "temperature": temperature}
        self.options = {k: v for k, v in options.items() if v is not None}
        parts = urlsplit(self.base_url)
        self.server_address = parts.hostname
        self.server_port = parts.port or (443 if parts.scheme == "https" else 80)

    async def chat(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        body: dict = {"model": self.model, "messages": messages, "tools": tools, "stream": False}
        if self.options:
            body["options"] = self.options
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=body)
                _raise_for_invalid_tool_call(resp)
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise LLMUnavailable(str(exc)) from exc

        message = data.get("message") or {}
        return LLMResponse(
            content=message.get("content") or "",
            tool_calls=[_parse_tool_call(tc) for tc in message.get("tool_calls") or []],
            finish_reason=data.get("done_reason"),
            model=data.get("model"),
            input_tokens=data.get("prompt_eval_count"),
            output_tokens=data.get("eval_count"),
        )


def _raise_for_invalid_tool_call(resp: httpx.Response) -> None:
    """Ollama answers 500 when the model writes malformed tool-call JSON."""
    if resp.status_code != 500:
        return
    try:
        error = resp.json().get("error", "")
    except ValueError:
        return
    if "invalid tool call" in error:
        raise InvalidToolCall(error)


def _parse_tool_call(raw: dict) -> ToolCall:
    fn = raw.get("function") or {}
    args = fn.get("arguments") or {}
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except ValueError:
            args = {}
    if not isinstance(args, dict):
        args = {}
    return ToolCall(id=raw.get("id") or f"call_{uuid.uuid4().hex[:12]}", name=fn.get("name", ""), arguments=args)
