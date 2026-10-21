from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_url: str = "redis://redis:6379"
    database_url: str = "postgresql://byteorder:byteorder@postgres:5432/byteorder"

    class Config:
        env_file = ".env"


settings = Settings()
