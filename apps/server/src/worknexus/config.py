from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WORKNEXUS_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://worknexus:worknexus@localhost:5432/worknexus"
    secret_key: str = "change-me-in-production"
    environment: str = "development"

    ai_platform_base_url: str = "http://localhost:8123"
    ai_platform_api_key: str = ""
    ai_platform_default_agent_id: str = ""
    # Which AIClient the workchat run uses: "multirag" (real SSE) or "fake" (deterministic,
    # for tests / E2E / offline dev). The real endpoint/body must be live-verified — see
    # docs/modules/workchat.md §11.
    ai_client: str = "multirag"
    ai_platform_timeout_seconds: float = 60.0

    # Intake triage provider (decision A). v0.1 only "rules" (deterministic, no external dep);
    # a "multirag" provider slots in after the AI endpoint is live-verified.
    intake_triage_provider: str = "rules"

    # Dashboard AI insights provider (M7 decision A, roadmap D7). v0.1 only "rules"
    # (deterministic, computed on demand from aggregated metrics); a "multirag" provider
    # slots in once the AI endpoint is live-verified.
    dashboard_insights_provider: str = "rules"

    mcp_auth_token: str = "change-me-mcp-token"

    cors_origins: list[str] = ["http://localhost:5173"]

    session_cookie_name: str = "worknexus_session"
    session_ttl_days: int = 7
    delegation_token_ttl_seconds: int = Field(default=600, ge=300, le=600)
    # How long a pending AgentAction stays confirmable before it lapses to `expired`.
    agent_action_pending_ttl_seconds: int = Field(default=604800, ge=300)
    bcrypt_rounds: int = 12
    invite_ttl_days: int = 7


@lru_cache
def get_settings() -> Settings:
    return Settings()
