"""intake MCP tools: registration + risk tags, and that the two low_write tools defer
into a pending AgentAction through the /mcp middleware (mirrors the work_items pattern)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from fastmcp.server.middleware import MiddlewareContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.config import get_settings
from worknexus.core.deps import Actor, ActorType
from worknexus.mcp import mcp
from worknexus.modules.identity import service as identity_service
from worknexus.modules.skills import middleware as mw

pytestmark = pytest.mark.p1

EXPECTED_TAGS = {
    "intake_list_intake_requests": "read",
    "intake_create_intake_request": "low_write",
    "intake_accept_intake_request": "low_write",
}


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


async def test_intake_tools_registered_with_risk_tags() -> None:
    by_name = {t.name: t for t in await mcp.list_tools()}
    for name, tag in EXPECTED_TAGS.items():
        assert name in by_name, f"{name} not registered"
        assert tag in (by_name[name].tags or set())


@pytest.mark.parametrize(
    ("tool", "arguments", "expected_action"),
    [
        (
            "intake_create_intake_request",
            {"title": "Lead from sales", "description": "wants SSO"},
            "create_intake_request",
        ),
        (
            "intake_accept_intake_request",
            {"intake_request_id": "intake_x", "type": "requirement"},
            "accept_intake_request",
        ),
    ],
)
async def test_low_write_intake_tool_defers_to_agent_action(
    monkeypatch: pytest.MonkeyPatch,
    db: AsyncSession,
    initialized: SimpleNamespace,
    tool: str,
    arguments: dict[str, object],
    expected_action: str,
) -> None:
    from worknexus.modules.workchat.models import AgentAction
    from worknexus.modules.workchat.schemas import AgentActionStatus

    token = await _issue_token(db, initialized)
    _patch(monkeypatch, db, {"authorization": f"Bearer {get_settings().mcp_auth_token}", mw.DELEGATION_HEADER: token})
    spy = _Spy()

    result = await mw.SkillInvocationMiddleware().on_call_tool(_context(tool, arguments), spy)

    # The tool body never runs; a pending AgentAction is created and a normal result returned.
    assert spy.called is False
    assert result.structured_content["status"] == "pending_confirmation"

    action = (await db.execute(select(AgentAction))).scalar_one()
    assert action.status == AgentActionStatus.PENDING
    assert action.action_type == expected_action
    assert action.arguments == arguments
    assert action.requested_by_user_id == initialized.owner.id
    assert action.project_id == initialized.project.id
