"""HTTP-level /mcp smoke test: real headers must reach the FastMCP middleware.

Kept minimal (the streamable-http handshake is brittle) — the dual-token rule matrix
is covered by the middleware unit tests. Both assertions run under a single lifespan
because the StreamableHTTP session manager can only be started once per app instance.
"""

from types import SimpleNamespace

import httpx
import pytest
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.exceptions import ToolError
from httpx import ASGITransport
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.config import get_settings
from worknexus.core.deps import Actor, ActorType
from worknexus.modules.identity import service as identity_service
from worknexus.modules.skills import middleware as mw
from worknexus.modules.skills.models import SkillInvocation

pytestmark = [pytest.mark.p1, pytest.mark.integration]


def _transport(app: object, headers: dict[str, str]) -> StreamableHttpTransport:
    def factory(
        *,
        headers: dict[str, str] | None = None,
        auth: httpx.Auth | None = None,
        follow_redirects: bool = True,
        timeout: httpx.Timeout | None = None,
    ) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=headers,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout or httpx.Timeout(30.0, read=60.0),
        )

    return StreamableHttpTransport(url="http://test/mcp/", headers=headers, httpx_client_factory=factory)


async def test_mcp_dual_token_smoke(
    monkeypatch: pytest.MonkeyPatch, db: AsyncSession, initialized: SimpleNamespace
) -> None:
    from contextlib import asynccontextmanager

    from worknexus.main import app

    @asynccontextmanager
    async def _fake_open():
        yield db

    monkeypatch.setattr(mw, "open_session", lambda: _fake_open())

    owner_actor = Actor(id=initialized.owner.id, type=ActorType.USER, tenant_id=initialized.tenant.id)
    issued = await identity_service.issue_delegation_token(
        db, owner_actor, user_id=initialized.owner.id, agent_id=initialized.agent.id, project_id=None
    )
    server_token = get_settings().mcp_auth_token

    async with app.router.lifespan_context(app):
        # 1. missing server token → rejected, no execution
        no_token = Client(_transport(app, {mw.DELEGATION_HEADER: issued.token}))
        with pytest.raises(ToolError):
            async with no_token as client:
                await client.call_tool("system_ping", {})

        # 2. valid server token + delegation → read tool runs, invocation logged
        authed = Client(
            _transport(
                app,
                {"Authorization": f"Bearer {server_token}", mw.DELEGATION_HEADER: issued.token},
            )
        )
        async with authed as client:
            result = await client.call_tool("system_ping", {})
        assert result.data["status"] == "ok"

    total = (await db.execute(select(func.count()).select_from(SkillInvocation))).scalar_one()
    assert total == 1
    inv = (await db.execute(select(SkillInvocation))).scalar_one()
    assert inv.tool_name == "system_ping"
    assert inv.status == "success"
    assert inv.represented_user_id == initialized.owner.id
