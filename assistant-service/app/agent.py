"""The agent loop, traced with OpenTelemetry GenAI semantic conventions.

Each customer message produces one `invoke_agent` span. Inside it, every call
to the model is a `chat` span and every tool call an `execute_tool` span.
Dash0 evals judge spans that carry `gen_ai.operation.name`.
"""
import json
import time
from dataclasses import dataclass

from opentelemetry import metrics, trace
from opentelemetry.trace import SpanKind, Status, StatusCode

from app import genai, tools
from app.llm import ChatModel, InvalidToolCall, LLMResponse
from app.menu import Menu
from app.prompts import build_system_prompt

AGENT_NAME = "byteorder-assistant"
FALLBACK_REPLY = (
    "Sorry, I couldn't sort that out. You can build your order from the menu instead, "
    "or ask the kitchen staff for help."
)


@dataclass
class TurnResult:
    reply: str
    draft: list[dict] | None = None
    draft_summary: str | None = None


class Agent:
    def __init__(
        self,
        llm: ChatModel,
        *,
        capture_content: bool,
        max_steps: int = 4,
        tracer: trace.Tracer | None = None,
        meter: metrics.Meter | None = None,
    ):
        self.llm = llm
        self.capture_content = capture_content
        self.max_steps = max_steps
        self.tracer = tracer or trace.get_tracer(__name__)
        meter = meter or metrics.get_meter(__name__)
        self.token_usage = meter.create_histogram(
            "gen_ai.client.token.usage", unit="{token}", description="Tokens used per model call"
        )
        self.duration = meter.create_histogram(
            "gen_ai.client.operation.duration", unit="s", description="Duration of model calls"
        )

    def _common_attributes(self) -> dict:
        return {
            "gen_ai.provider.name": self.llm.provider,
            "gen_ai.request.model": self.llm.model,
        }

    async def run(
        self,
        *,
        menu: Menu,
        conversation: list[dict],
        customer_name: str | None,
        kitchen_name: str,
        kitchen_id: str,
        conversation_id: str | None,
    ) -> TurnResult:
        system = build_system_prompt(kitchen_name, customer_name, menu.summary())
        messages = [{"role": "system", "content": system}, *conversation]

        attributes = {
            "gen_ai.operation.name": "invoke_agent",
            "gen_ai.agent.name": AGENT_NAME,
            "byteorder.kitchen_id": kitchen_id,
            **self._common_attributes(),
        }
        if conversation_id:
            attributes["gen_ai.conversation.id"] = conversation_id

        with self.tracer.start_as_current_span(
            f"invoke_agent {AGENT_NAME}", kind=SpanKind.INTERNAL, attributes=attributes,
            record_exception=False, set_status_on_exception=False,
        ) as span:
            if self.capture_content:
                span.set_attribute("gen_ai.system_instructions", genai.system_instructions(messages))
                span.set_attribute("gen_ai.input.messages", genai.input_messages(conversation))
            try:
                result, usage, steps, hit_limit = await self._loop(messages, menu)
            except Exception as exc:
                span.set_attribute("error.type", type(exc).__name__)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                raise

            span.set_attribute("gen_ai.usage.input_tokens", usage[0])
            span.set_attribute("gen_ai.usage.output_tokens", usage[1])
            span.set_attribute("byteorder.assistant.steps", steps)
            span.set_attribute("byteorder.assistant.step_limit_reached", hit_limit)
            span.set_attribute("byteorder.assistant.draft_items", len(result.draft or []))
            if self.capture_content:
                span.set_attribute("gen_ai.output.messages", genai.text_output(result.reply))
            return result

    async def _loop(self, messages: list[dict], menu: Menu):
        draft = draft_summary = None
        input_tokens = output_tokens = 0
        span = trace.get_current_span()
        invalid_tool_calls = 0
        span.set_attribute("byteorder.assistant.invalid_tool_calls", 0)

        for step in range(1, self.max_steps + 1):
            try:
                response = await self._chat(messages)
            except InvalidToolCall:
                # The attempt is visible as a failed chat span; try the step again.
                invalid_tool_calls += 1
                span.set_attribute("byteorder.assistant.invalid_tool_calls", invalid_tool_calls)
                continue
            input_tokens += response.input_tokens or 0
            output_tokens += response.output_tokens or 0

            messages.append(_assistant_message(response))
            if not response.tool_calls:
                reply = response.content.strip() or FALLBACK_REPLY
                return TurnResult(reply, draft, draft_summary), (input_tokens, output_tokens), step, False

            for call in response.tool_calls:
                outcome = self._execute_tool(call.id, call.name, call.arguments, menu)
                if outcome.draft is not None:
                    draft, draft_summary = outcome.draft, outcome.draft_summary
                messages.append(
                    {"role": "tool", "tool_call_id": call.id, "tool_name": call.name, "content": outcome.result}
                )

        return TurnResult(FALLBACK_REPLY, draft, draft_summary), (input_tokens, output_tokens), self.max_steps, True

    async def _chat(self, messages: list[dict]) -> LLMResponse:
        attributes = {
            "gen_ai.operation.name": "chat",
            **self._common_attributes(),
        }
        if self.llm.server_address:
            attributes["server.address"] = self.llm.server_address
        if self.llm.server_port:
            attributes["server.port"] = self.llm.server_port

        with self.tracer.start_as_current_span(
            f"chat {self.llm.model}", kind=SpanKind.CLIENT, attributes=attributes,
            record_exception=False, set_status_on_exception=False,
        ) as span:
            if self.capture_content:
                span.set_attribute("gen_ai.system_instructions", genai.system_instructions(messages))
                span.set_attribute("gen_ai.input.messages", genai.input_messages(messages))

            started = time.monotonic()
            metric_attrs = {"gen_ai.operation.name": "chat", **self._common_attributes()}
            try:
                response = await self.llm.chat(messages, tools.TOOLS)
            except InvalidToolCall as exc:
                span.set_attribute("error.type", "invalid_tool_call")
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                self.duration.record(time.monotonic() - started, {**metric_attrs, "error.type": "invalid_tool_call"})
                raise
            except Exception as exc:
                span.set_attribute("error.type", type(exc).__name__)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                self.duration.record(time.monotonic() - started, {**metric_attrs, "error.type": type(exc).__name__})
                raise
            self.duration.record(time.monotonic() - started, metric_attrs)

            if response.model:
                span.set_attribute("gen_ai.response.model", response.model)
                metric_attrs["gen_ai.response.model"] = response.model
            span.set_attribute("gen_ai.response.finish_reasons", [response.finish_reason or "stop"])
            if response.input_tokens is not None:
                span.set_attribute("gen_ai.usage.input_tokens", response.input_tokens)
                self.token_usage.record(response.input_tokens, {**metric_attrs, "gen_ai.token.type": "input"})
            if response.output_tokens is not None:
                span.set_attribute("gen_ai.usage.output_tokens", response.output_tokens)
                self.token_usage.record(response.output_tokens, {**metric_attrs, "gen_ai.token.type": "output"})
            if self.capture_content:
                span.set_attribute("gen_ai.output.messages", genai.output_messages(response))
            return response

    def _execute_tool(self, call_id: str, name: str, arguments: dict, menu: Menu) -> tools.ToolOutcome:
        attributes = {
            "gen_ai.operation.name": "execute_tool",
            "gen_ai.tool.name": name,
            "gen_ai.tool.call.id": call_id,
            "gen_ai.tool.type": "function",
        }
        with self.tracer.start_as_current_span(
            f"execute_tool {name}", kind=SpanKind.INTERNAL, attributes=attributes
        ) as span:
            if self.capture_content:
                span.set_attribute("gen_ai.tool.call.arguments", json.dumps(arguments, ensure_ascii=False))
            outcome = tools.execute(name, arguments, menu)
            if self.capture_content:
                span.set_attribute("gen_ai.tool.call.result", outcome.result)
            if outcome.error_type:
                span.set_attribute("error.type", outcome.error_type)
                span.set_status(Status(StatusCode.ERROR, outcome.error_type))
            return outcome


def _assistant_message(response: LLMResponse) -> dict:
    message: dict = {"role": "assistant", "content": response.content}
    if response.tool_calls:
        message["tool_calls"] = [
            {"id": c.id, "function": {"name": c.name, "arguments": c.arguments}} for c in response.tool_calls
        ]
    return message
