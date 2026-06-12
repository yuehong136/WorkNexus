from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WORKNEXUS_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://worknexus:worknexus@localhost:5432/worknexus"
    secret_key: str = "change-me-in-production"
    environment: str = "development"

    ai_platform_base_url: str = "http://localhost:8123"
    ai_platform_api_key: str = ""

    mcp_auth_token: str = "change-me-mcp-token"

    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
