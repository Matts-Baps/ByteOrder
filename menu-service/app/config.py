from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://byteorder:byteorder@postgres:5432/byteorder"

    class Config:
        env_file = ".env"


settings = Settings()
