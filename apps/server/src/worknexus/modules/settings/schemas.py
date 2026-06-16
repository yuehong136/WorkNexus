from worknexus.core.schemas import ApiModel


class AiConnectionOut(ApiModel):
    """Masked, read-only view of the multirag connection (.env-driven, D7). The API token is
    NEVER returned in plaintext — only whether it is configured and a masked tail."""

    ai_client: str
    ai_platform_base_url: str
    ai_platform_default_agent_id: str
    ai_platform_timeout_seconds: float
    api_key_configured: bool
    api_key_masked: str | None
    intake_triage_provider: str
    dashboard_insights_provider: str
