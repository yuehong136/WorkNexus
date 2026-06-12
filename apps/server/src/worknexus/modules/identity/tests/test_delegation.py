"""Delegation token issue/verify service tests (D5)."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.errors import BizError, ErrorCode
from worknexus.modules.identity import service
from worknexus.modules.identity.models import McpDelegationToken

pytestmark = pytest.mark.integration


@pytest.mark.p0
async def test_issue_and_verify_roundtrip(db: AsyncSession, initialized: SimpleNamespace) -> None:
    actor = await service.resolve_session_actor(db, initialized.session.token)
    issued = await service.issue_delegation_token(
        db,
        actor,
        user_id=initialized.owner.id,
        agent_id=initialized.agent.id,
        project_id=initialized.project.id,
        conversation_id="conv-1",
        run_id="run-1",
    )
    assert issued.token.startswith("wn_del_")

    ctx = await service.verify_delegation_token(db, issued.token)
    assert ctx.tenant_id == initialized.tenant.id
    assert ctx.user_id == initialized.owner.id
    assert ctx.agent_id == initialized.agent.id
    assert ctx.project_id == initialized.project.id
    assert ctx.conversation_id == "conv-1"
    assert ctx.run_id == "run-1"

    row = (await db.execute(select(McpDelegationToken))).scalar_one()
    assert row.token_hash == service.hash_token(issued.token)
    assert row.last_used_at is not None


@pytest.mark.p1
async def test_snapshot_is_user_agent_intersection(db: AsyncSession, initialized: SimpleNamespace) -> None:
    actor = await service.resolve_session_actor(db, initialized.session.token)
    issued = await service.issue_delegation_token(
        db, actor, user_id=initialized.owner.id, agent_id=initialized.agent.id, project_id=initialized.project.id
    )
    ctx = await service.verify_delegation_token(db, issued.token)
    snapshot = ctx.permissions_snapshot
    assert set(snapshot) == {"user", "agent", "effective"}
    effective = set(snapshot["effective"])
    assert effective == set(snapshot["user"]) & set(snapshot["agent"])
    # The owner lacks skill.invoke, so it must not survive the intersection.
    assert "skill.invoke" in snapshot["agent"]
    assert "skill.invoke" not in effective
    assert "work_item.create" in effective


@pytest.mark.p1
async def test_verify_rejects_unknown_token(db: AsyncSession, initialized: SimpleNamespace) -> None:
    with pytest.raises(BizError) as excinfo:
        await service.verify_delegation_token(db, "wn_del_not-real")
    assert excinfo.value.code == ErrorCode.DELEGATION_TOKEN_INVALID


@pytest.mark.p1
async def test_verify_rejects_expired_token(db: AsyncSession, initialized: SimpleNamespace) -> None:
    actor = await service.resolve_session_actor(db, initialized.session.token)
    issued = await service.issue_delegation_token(
        db, actor, user_id=initialized.owner.id, agent_id=initialized.agent.id
    )
    row = (await db.execute(select(McpDelegationToken))).scalar_one()
    row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db.flush()
    with pytest.raises(BizError) as excinfo:
        await service.verify_delegation_token(db, issued.token)
    assert excinfo.value.code == ErrorCode.DELEGATION_TOKEN_EXPIRED


@pytest.mark.p1
async def test_verify_rejects_revoked_token(db: AsyncSession, initialized: SimpleNamespace) -> None:
    actor = await service.resolve_session_actor(db, initialized.session.token)
    issued = await service.issue_delegation_token(
        db, actor, user_id=initialized.owner.id, agent_id=initialized.agent.id
    )
    row = (await db.execute(select(McpDelegationToken))).scalar_one()
    row.revoked_at = datetime.now(UTC)
    await db.flush()
    with pytest.raises(BizError) as excinfo:
        await service.verify_delegation_token(db, issued.token)
    assert excinfo.value.code == ErrorCode.DELEGATION_TOKEN_INVALID


@pytest.mark.p1
async def test_issue_rejects_disabled_user_and_unknown_agent(db: AsyncSession, initialized: SimpleNamespace) -> None:
    actor = await service.resolve_session_actor(db, initialized.session.token)
    with pytest.raises(BizError) as excinfo:
        await service.issue_delegation_token(db, actor, user_id=initialized.owner.id, agent_id="missing")
    assert excinfo.value.code == ErrorCode.NOT_FOUND

    initialized.owner.status = "disabled"
    await db.flush()
    with pytest.raises(BizError) as excinfo:
        await service.issue_delegation_token(db, actor, user_id=initialized.owner.id, agent_id=initialized.agent.id)
    assert excinfo.value.code == ErrorCode.USER_DISABLED


@pytest.mark.p1
async def test_token_reusable_within_ttl(db: AsyncSession, initialized: SimpleNamespace) -> None:
    actor = await service.resolve_session_actor(db, initialized.session.token)
    issued = await service.issue_delegation_token(
        db, actor, user_id=initialized.owner.id, agent_id=initialized.agent.id
    )
    first = await service.verify_delegation_token(db, issued.token)
    second = await service.verify_delegation_token(db, issued.token)
    assert first.user_id == second.user_id
