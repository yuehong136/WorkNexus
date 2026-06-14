"""Middleware unit tests: monkeypatch get_http_headers + manual MiddlewareContext.

The in-memory FastMCP client carries no HTTP headers, so the dual-token gate is
exercised by calling `on_call_tool` directly with injected headers and a session
bound to the rolled-back test transaction.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import MiddlewareContext
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.config import get_settings
from worknexus.core.deps import Actor, ActorType
from worknexus.modules.identity import service as identity_service
from worknexus.modules.skills import middleware as mw
from worknexus.modules.skills.models import SkillInvocation
from worknexus.modules.skills.schemas import SkillInvocationStatus

pytestmark = pytest.mark.p1


class _Spy:
    def __init__(self, *, raises: Exception | None = None) -> None:
        self.called = False
        self.raises = raises

    async def __call__(self, _context: object) -> dict[str, str]:
        self.called = True
        if self.raises is not None:
            raise self.raises
        return {"status": "ok"}


def _patch(monkeypatch: pytest.MonkeyPatch, db: AsyncSession, headers: dict[str, str]) -> None:
    @asynccontextmanager
    async def _fake_open() -> AsyncIterator[AsyncSession]:
        yield db

    monkeypatch.setattr(mw, "open_session", lambda: _fake_open())
    monkeypatch.setattr(mw, "get_http_headers", lambda **_: headers)


async def _issue_token(db: AsyncSession, initialized: SimpleNamespace, *, project_id: str | None) -> str:
    owner_actor = Actor(id=initialized.owner.id, type=ActorType.USER, tenant_id=initialized.tenant.id)
    issued = await identity_service.issue_delegation_token(
        db, owner_actor, user_id=initialized.owner.id, agent_id=initialized.agent.id, project_id=project_id
    )
    return issued.token


def _context(name: str, arguments: dict[str, object]) -> MiddlewareContext:
    return MiddlewareContext(message=SimpleNamespace(name=name, arguments=arguments))


async def _count(db: AsyncSession) -> int:
    return (await db.execute(select(func.count()).select_from(SkillInvocation))).scalar_one()


async def test_read_tool_executes_and_logs_success(
    monkeypatch: pytest.MonkeyPatch, db: AsyncSession, initialized: SimpleNamespace
) -> None:
    token = await _issue_token(db, initialized, project_id=None)
    _patch(monkeypatch, db, {"authorization": f"Bearer {get_settings().mcp_auth_token}", mw.DELEGATION_HEADER: token})
    spy = _Spy()

    result = await mw.SkillInvocationMiddleware().on_call_tool(_context("system_ping", {}), spy)

    assert spy.called is True
    assert result == {"status": "ok"}
    inv = (await db.execute(select(SkillInvocation))).scalar_one()
    assert inv.status == SkillInvocationStatus.SUCCESS
    assert inv.tool_name == "system_ping"
    assert inv.represented_user_id == initialized.owner.id


async def test_low_write_tool_deferred_to_agent_action(
    monkeypatch: pytest.MonkeyPatch, db: AsyncSession, initialized: SimpleNamespace
) -> None:
    from worknexus.modules.workchat.models import AgentAction
    from worknexus.modules.workchat.schemas import AgentActionStatus, AgentActionType

    token = await _issue_token(db, initialized, project_id=initialized.project.id)
    _patch(monkeypatch, db, {"authorization": f"Bearer {get_settings().mcp_auth_token}", mw.DELEGATION_HEADER: token})
    spy = _Spy()

    result = await mw.SkillInvocationMiddleware().on_call_tool(
        _context("workitem_create_work_item", {"title": "x", "type": "task"}), spy
    )

    # The tool body never runs; a pending AgentAction is created and a normal result returned.
    assert spy.called is False
    assert result.structured_content["status"] == "pending_confirmation"
    assert result.structured_content["requiresConfirmation"] is True

    action = (await db.execute(select(AgentAction))).scalar_one()
    assert action.status == AgentActionStatus.PENDING
    assert action.action_type == AgentActionType.CREATE_WORK_ITEM
    assert action.arguments == {"title": "x", "type": "task"}
    assert action.requested_by_user_id == initialized.owner.id
    assert action.project_id == initialized.project.id

    inv = (await db.execute(select(SkillInvocation))).scalar_one()
    assert inv.status == SkillInvocationStatus.SUCCESS
    assert inv.requires_confirmation is True
    assert inv.agent_action_id == action.id


async def test_failing_read_tool_logs_failure(
    monkeypatch: pytest.MonkeyPatch, db: AsyncSession, initialized: SimpleNamespace
) -> None:
    token = await _issue_token(db, initialized, project_id=None)
    _patch(monkeypatch, db, {"authorization": f"Bearer {get_settings().mcp_auth_token}", mw.DELEGATION_HEADER: token})
    spy = _Spy(raises=RuntimeError("boom"))

    with pytest.raises(RuntimeError):
        await mw.SkillInvocationMiddleware().on_call_tool(_context("system_ping", {}), spy)

    inv = (await db.execute(select(SkillInvocation))).scalar_one()
    assert inv.status == SkillInvocationStatus.FAILED
    assert inv.error_message is not None and "boom" in inv.error_message


async def test_missing_server_token_rejected_before_db(
    monkeypatch: pytest.MonkeyPatch, db: AsyncSession, initialized: SimpleNamespace
) -> None:
    token = await _issue_token(db, initialized, project_id=None)
    _patch(monkeypatch, db, {mw.DELEGATION_HEADER: token})  # no Authorization
    spy = _Spy()

    with pytest.raises(ToolError):
        await mw.SkillInvocationMiddleware().on_call_tool(_context("system_ping", {}), spy)

    assert spy.called is False
    assert await _count(db) == 0


async def test_invalid_delegation_rejected(
    monkeypatch: pytest.MonkeyPatch, db: AsyncSession, initialized: SimpleNamespace
) -> None:
    _patch(
        monkeypatch,
        db,
        {"authorization": f"Bearer {get_settings().mcp_auth_token}", mw.DELEGATION_HEADER: "wn_del_bogus"},
    )
    spy = _Spy()

    with pytest.raises(ToolError):
        await mw.SkillInvocationMiddleware().on_call_tool(_context("system_ping", {}), spy)

    assert spy.called is False
    assert await _count(db) == 0
