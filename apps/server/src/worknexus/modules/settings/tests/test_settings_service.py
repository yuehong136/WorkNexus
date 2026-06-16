"""settings.service.get_ai_connection: the API token is masked and never leaks plaintext."""

import pytest

from worknexus.config import Settings
from worknexus.modules.settings import service

pytestmark = pytest.mark.p1


def test_masks_api_key_and_never_leaks_plaintext() -> None:
    settings = Settings(ai_platform_api_key="supersecret-zzzz9999")
    out = service.get_ai_connection(settings)

    assert out.api_key_configured is True
    assert out.api_key_masked == "••••9999"
    dumped = out.model_dump_json()
    assert "supersecret" not in dumped
    assert "supersecret-zzzz9999" not in dumped


def test_unconfigured_key_is_none() -> None:
    out = service.get_ai_connection(Settings(ai_platform_api_key=""))
    assert out.api_key_configured is False
    assert out.api_key_masked is None


def test_passthrough_non_secret_fields() -> None:
    settings = Settings(
        ai_client="fake",
        ai_platform_base_url="http://platform.test:8123",
        ai_platform_default_agent_id="agent-123",
    )
    out = service.get_ai_connection(settings)
    assert out.ai_client == "fake"
    assert out.ai_platform_base_url == "http://platform.test:8123"
    assert out.ai_platform_default_agent_id == "agent-123"
