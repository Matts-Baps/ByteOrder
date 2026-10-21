import logging
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from opentelemetry import metrics

from app.agent import Agent
from app.config import Settings
from app.llm import ChatModel, LLMUnavailable, OllamaChat
from app.menu_client import MenuUnavailable, fetch_menu
from app.ratelimit import RateLimiter
from app.telemetry import setup_telemetry

log = logging.getLogger(__name__)

MAX_MESSAGES = 20
MAX_MESSAGE_LENGTH = 1000


class ChatMessage(BaseModel):
    # Only customer and assistant turns are accepted. System and tool messages
    # are always built by the server, so a client cannot inject them.
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=MAX_MESSAGES)
    customer_name: str | None = Field(default=None, max_length=200)
    conversation_id: str | None = Field(default=None, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")

    @field_validator("messages")
    @classmethod
    def last_message_from_customer(cls, messages: list[ChatMessage]) -> list[ChatMessage]:
        if messages and messages[-1].role != "user":
            raise ValueError("The last message must come from the customer")
        return messages


class Draft(BaseModel):
    items: list[dict]
    summary: str


class ChatResponse(BaseModel):
    reply: str
    draft: Draft | None


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def create_app(
    settings: Settings | None = None,
    llm: ChatModel | None = None,
    limiter: RateLimiter | None = None,
) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="ByteOrder assistant")
    setup_telemetry(app)

    llm = llm or OllamaChat(
        settings.ollama_url,
        settings.ollama_model,
        num_ctx=settings.ollama_num_ctx,
        timeout=settings.ollama_timeout_seconds,
        max_output_tokens=settings.ollama_max_output_tokens,
        temperature=settings.ollama_temperature,
    )
    if limiter is None:
        from redis.asyncio import Redis

        limiter = RateLimiter(
            Redis.from_url(settings.redis_url),
            per_client=settings.rate_limit_per_client_per_minute,
            per_kitchen=settings.rate_limit_per_kitchen_per_minute,
        )
    agent = Agent(llm, capture_content=settings.capture_message_content, max_steps=settings.max_steps)
    rate_limited = metrics.get_meter(__name__).create_counter(
        "byteorder.assistant.rate_limited", unit="{request}", description="Chat requests refused by the rate limiter"
    )

    def kitchen_id_for(header_value: str | None) -> str:
        if settings.auth_mode == "self-hosted":
            return settings.default_kitchen_id
        if not header_value:
            raise HTTPException(status_code=400, detail="X-Kitchen-ID header is required")
        return header_value

    @app.get("/health")
    def health():
        return {"status": "ok", "model": settings.ollama_model}

    @app.post("/chat", response_model=ChatResponse)
    async def chat(
        payload: ChatRequest,
        request: Request,
        x_kitchen_id: str | None = Header(default=None, alias="x-kitchen-id"),
    ):
        kitchen_id = kitchen_id_for(x_kitchen_id)
        if not await limiter.allow(_client_key(request), kitchen_id):
            rate_limited.add(1)
            raise HTTPException(status_code=429, detail="Too many messages, please wait a minute")

        try:
            menu, kitchen_name = await fetch_menu(settings.menu_service_url, kitchen_id)
        except MenuUnavailable:
            log.exception("Could not load menu")
            raise HTTPException(status_code=502, detail="Could not load the menu")

        try:
            result = await agent.run(
                menu=menu,
                conversation=[m.model_dump() for m in payload.messages],
                customer_name=payload.customer_name,
                kitchen_name=kitchen_name,
                kitchen_id=kitchen_id,
                conversation_id=payload.conversation_id,
            )
        except LLMUnavailable:
            log.exception("Model unavailable")
            raise HTTPException(status_code=503, detail="The assistant is unavailable right now")

        draft = Draft(items=result.draft, summary=result.draft_summary) if result.draft else None
        return ChatResponse(reply=result.reply, draft=draft)

    return app
