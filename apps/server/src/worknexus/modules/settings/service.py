"""settings service: read-only, masked view of system config (v0.1 is .env-driven, D7).

No DB, no write, no audit. The only contract that matters here is that the API token never
leaves the server in plaintext."""

from worknexus.config import Settings
from worknexus.modules.settings.schemas import AiConnectionOut


def _mask(secret: str) -> str | None:
    """Reveal only the last 4 chars; never return the plaintext token. Empty -> None."""
    if not secret:
        return None
    return f"••••{secret[-4:]}" if len(secret) >= 4 else "••••"


def get_ai_connection(settings: Settings) -> AiConnectionOut:
    return AiConnectionOut(
        ai_client=settings.ai_client,
        ai_platform_base_url=settings.ai_platform_base_url,
        ai_platform_default_agent_id=settings.ai_platform_default_agent_id,
        ai_platform_timeout_seconds=settings.ai_platform_timeout_seconds,
        api_key_configured=bool(settings.ai_platform_api_key),
        api_key_masked=_mask(settings.ai_platform_api_key),
        intake_triage_provider=settings.intake_triage_provider,
        dashboard_insights_provider=settings.dashboard_insights_provider,
    )
