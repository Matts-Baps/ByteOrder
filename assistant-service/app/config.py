from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(populate_by_name=True)

    ollama_url: str = "http://ollama:11434"
    ollama_model: str = "qwen3:4b-instruct"
    # Leave unset to use the model server's default. Changing it makes Ollama
    # reload the model, which slows down anything else sharing it.
    ollama_num_ctx: int | None = None
    ollama_timeout_seconds: float = 60.0
    # Caps each reply so a confused model cannot generate until the timeout.
    ollama_max_output_tokens: int = 512
    ollama_temperature: float | None = None

    menu_service_url: str = "http://menu-service:8000"
    redis_url: str = "redis://redis:6379"

    auth_mode: str = "cloud"
    default_kitchen_id: str = "default"

    max_steps: int = 4
    rate_limit_per_client_per_minute: int = 10
    rate_limit_per_kitchen_per_minute: int = 60

    # Standard variable used by OpenTelemetry GenAI instrumentations. Dash0 evals
    # that judge conversations need this switched on.
    capture_message_content: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "capture_message_content", "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"
        ),
    )
