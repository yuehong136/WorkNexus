"""settings REST: ai_agent.manage gate (admin/owner) + masked envelope."""

from types import SimpleNamespace

import pytest
from httpx import AsyncClient

from worknexus.modules.identity.models import User

pytestmark = pytest.mark.integration

API = "/api/v1"


@pytest.mark.p1
async def test_owner_reads_masked_ai_connection(owner_client: AsyncClient, initialized: SimpleNamespace) -> None:
    body = (await owner_client.get(f"{API}/settings/ai-connection")).json()
    assert body["code"] == 0
    data = body["data"]
    assert "aiClient" in data and "apiKeyConfigured" in data
    assert "aiPlatformApiKey" not in data  # the raw field is never serialized
    if data["apiKeyConfigured"]:
        assert data["apiKeyMasked"].startswith("••••")
        assert len(data["apiKeyMasked"]) <= 8


@pytest.mark.p1
async def test_member_forbidden(client: AsyncClient, initialized: SimpleNamespace, member_user: User) -> None:
    login = await client.post(f"{API}/auth/login", json={"email": "member@example.com", "password": "member-pass-123"})
    assert login.json()["code"] == 0
    assert (await client.get(f"{API}/settings/ai-connection")).status_code == 403


@pytest.mark.p1
async def test_unauthenticated_is_401(client: AsyncClient, initialized: SimpleNamespace) -> None:
    assert (await client.get(f"{API}/settings/ai-connection")).status_code == 401
