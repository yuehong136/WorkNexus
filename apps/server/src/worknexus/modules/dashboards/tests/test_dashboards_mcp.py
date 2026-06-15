"""dashboards MCP tool: registration + read tag, delegation guard, and that the read tool
executes through the /mcp middleware and writes a skill_invocation."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import MiddlewareContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.config import get_settings
from worknexus.core.deps import Actor, ActorType
from worknexus.mcp import mcp
from worknexus.modules.identity import service as identity_service
from worknexus.modules.skills import middleware as mw
from worknexus.modules.skills.models import SkillInvocation
from worknexus.modules.skills.schemas import RiskLevel, SkillInvocationStatus

pytestmark = pytest.mark.p1

TOOL = "dashboard_get_project_dashboard"


class _Spy:
    def __init__(self) -> None:
        self.called = False

    async def __call__(self, _context: object) -> dict[str, str]:
        self.called = True
        return {"status": "ok"}


def _patch(monkeypatch: pytest.MonkeyPatch, db: AsyncSession, headers: dict[str, str]) -> None:
    @asynccontextmanager
    async def _fake_open() -> AsyncIterator[AsyncSession]:
        yield db

    monkeypatch.setattr(mw, "open_session", lambda: _fake_open())
    monkeypatch.setattr(mw, "get_http_headers", lambda **_: headers)


async def _issue_token(db: AsyncSession, initialized: SimpleNamespace) -> str:
    owner_actor = Actor(id=initialized.owner.id, type=ActorType.USER, tenant_id=initialized.tenant.id)
    issued = await identity_service.issue_delegation_token(
        db, owner_actor, user_id=initialized.owner.id, agent_id=initialized.agent.id, project_id=initialized.project.id
    )
    return issued.token


def _context(name: str, arguments: dict[str, object]) -> MiddlewareContext:
    return MiddlewareContext(message=SimpleNamespace(name=name, arguments=arguments))


async def test_dashboard_tool_registered_with_read_tag() -> None:
    by_name = {t.name: t for t in await mcp.list_tools()}
    assert TOOL in by_name, f"{TOOL} not registered"
    assert "read" in (by_name[TOOL].tags or set())


async def test_read_tool_requires_delegation_token() -> None:
    async with Client(mcp) as client:
        with pytest.raises(ToolError):
            await client.call_tool(TOOL, {})


async def test_read_tool_executes_and_logs_invocation(
    monkeypatch: pytest.MonkeyPatch, db: AsyncSession, initialized: SimpleNamespace
) -> None:
    token = await _issue_token(db, initialized)
    _patch(monkeypatch, db, {"authorization": f"Bearer {get_settings().mcp_auth_token}", mw.DELEGATION_HEADER: token})
    spy = _Spy()

    result = await mw.SkillInvocationMiddleware().on_call_tool(_context(TOOL, {"overdue_limit": 5}), spy)

    # read risk -> executes directly (not deferred to an AgentAction) and logs success.
    assert spy.called is True
    assert result == {"status": "ok"}
    inv = (await db.execute(select(SkillInvocation))).scalar_one()
    assert inv.tool_name == TOOL
    assert inv.risk_level == RiskLevel.READ
    assert inv.status == SkillInvocationStatus.SUCCESS
    assert inv.requires_confirmation is False
