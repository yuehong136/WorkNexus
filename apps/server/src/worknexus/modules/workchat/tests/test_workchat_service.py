"""workchat service unit tests on a real (rolled-back) PostgreSQL session.

Covers the AgentAction confirmation chain: propose → approve (live double-check,
AI-agent-actor write, provenance) → executed / failed; reject; expiry; non-pending;
permission denial; and list scoping.
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.deps import Actor, ActorType
from worknexus.core.errors import BizError, ErrorCode
from worknexus.core.pagination import PageParams
from worknexus.modules.audit.models import AuditLog
from worknexus.modules.audit.service import AuditAction
from worknexus.modules.identity.models import User
from worknexus.modules.identity.schemas import DelegationContext
from worknexus.modules.work_items import service as work_items_service
from worknexus.modules.work_items.models import WorkItem
from worknexus.modules.work_items.schemas import WorkItemCreateIn, WorkItemSource, WorkItemType
from worknexus.modules.workchat import service
from worknexus.modules.workchat.models import AgentAction, Conversation
from worknexus.modules.workchat.schemas import AgentActionStatus, AgentActionType

pytestmark = pytest.mark.p1


def _user_actor(initialized: SimpleNamespace) -> Actor:
    return Actor(id=initialized.owner.id, type=ActorType.USER, tenant_id=initialized.tenant.id)


def _delegation(initialized: SimpleNamespace) -> DelegationContext:
    return DelegationContext(
        tenant_id=initialized.tenant.id,
        user_id=initialized.owner.id,
        agent_id=initialized.agent.id,
        project_id=initialized.project.id,
        conversation_id=None,
        run_id=None,
        permissions_snapshot={"user": [], "agent": [], "effective": ["work_item.create"]},
    )


async def _propose(
    db: AsyncSession,
    initialized: SimpleNamespace,
    *,
    tool: str = "workitem_create_work_item",
    arguments: dict[str, Any] | None = None,
) -> AgentAction:
    action = await service.create_pending_agent_action(
        db,
        _delegation(initialized),
        tool_name=tool,
        arguments=arguments if arguments is not None else {"title": "From AI", "type": "task"},
        skill_invocation_id="si_test_0001",
    )
    await db.commit()
    return action


async def test_default_conversation_is_idempotent(db: AsyncSession, initialized: SimpleNamespace) -> None:
    actor = _user_actor(initialized)
    first = await service.get_or_create_default_conversation(db, actor, initialized.project.id)
    second = await service.get_or_create_default_conversation(db, actor, initialized.project.id)
    assert first.id == second.id
    count = (await db.execute(select(func.count()).select_from(Conversation))).scalar_one()
    assert count == 1


async def test_propose_creates_pending_with_audit(db: AsyncSession, initialized: SimpleNamespace) -> None:
    action = await _propose(db, initialized)
    assert action.status == AgentActionStatus.PENDING
    assert action.action_type == AgentActionType.CREATE_WORK_ITEM
    assert action.requested_by_user_id == initialized.owner.id
    assert action.agent_id == initialized.agent.id
    assert action.project_id == initialized.project.id
    assert action.expires_at is not None
    audit_rows = (
        (
            await db.execute(
                select(AuditLog).where(
                    AuditLog.action == AuditAction.AI_PROPOSED_ACTION_CREATE, AuditLog.resource_id == action.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(audit_rows) == 1


async def test_approve_executes_and_records_provenance(db: AsyncSession, initialized: SimpleNamespace) -> None:
    action = await _propose(db, initialized, arguments={"title": "AI task", "type": "task"})
    out = await service.approve_and_execute(db, _user_actor(initialized), action.id)

    assert out.status == AgentActionStatus.EXECUTED
    assert out.result_ref_type == "work_item"
    assert out.approved_by_user_id == initialized.owner.id
    work_item = await db.get(WorkItem, out.result_ref_id)
    assert work_item is not None
    assert work_item.source == WorkItemSource.AI_CHAT
    assert work_item.source_ref_id == action.id
    # reporter is the requesting user (users FK); created_by carries the agent id.
    assert work_item.reporter_id == initialized.owner.id
    assert work_item.created_by == initialized.agent.id
    # AI authored the work item; the user approved the action — both audited.
    assert (
        await db.execute(
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.action == AuditAction.AGENT_ACTION_EXECUTE, AuditLog.resource_id == action.id)
        )
    ).scalar_one() == 1


async def test_approve_non_pending_rejected(db: AsyncSession, initialized: SimpleNamespace) -> None:
    action = await _propose(db, initialized)
    await service.approve_and_execute(db, _user_actor(initialized), action.id)
    with pytest.raises(BizError) as exc:
        await service.approve_and_execute(db, _user_actor(initialized), action.id)
    assert exc.value.code == ErrorCode.AGENT_ACTION_NOT_PENDING


async def test_approve_expired(db: AsyncSession, initialized: SimpleNamespace) -> None:
    action = await _propose(db, initialized)
    action.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db.commit()
    with pytest.raises(BizError) as exc:
        await service.approve_and_execute(db, _user_actor(initialized), action.id)
    assert exc.value.code == ErrorCode.AGENT_ACTION_EXPIRED
    refreshed = await db.get(AgentAction, action.id)
    assert refreshed is not None
    assert refreshed.status == AgentActionStatus.EXPIRED


async def test_approve_denied_for_user_without_permission(
    db: AsyncSession, initialized: SimpleNamespace, member_user: User
) -> None:
    action = await _propose(db, initialized)
    outsider = Actor(id=member_user.id, type=ActorType.USER, tenant_id=initialized.tenant.id)
    with pytest.raises(BizError) as exc:
        await service.approve_and_execute(db, outsider, action.id)
    assert exc.value.code == ErrorCode.FORBIDDEN
    refreshed = await db.get(AgentAction, action.id)
    assert refreshed is not None
    assert refreshed.status == AgentActionStatus.PENDING


async def test_approve_failed_dispatch_marks_failed(db: AsyncSession, initialized: SimpleNamespace) -> None:
    actor = _user_actor(initialized)
    created = await work_items_service.create_work_item(
        db, actor, initialized.project.id, WorkItemCreateIn(type=WorkItemType.TASK, title="seed")
    )
    # backlog -> done is not an allowed transition; the dispatch raises and the action fails.
    action = await _propose(
        db,
        initialized,
        tool="workitem_transition_work_item",
        arguments={"work_item_id": created.id, "status": "done"},
    )
    out = await service.approve_and_execute(db, actor, action.id)
    assert out.status == AgentActionStatus.FAILED
    assert out.error_message is not None


async def test_reject(db: AsyncSession, initialized: SimpleNamespace) -> None:
    action = await _propose(db, initialized)
    out = await service.reject(db, _user_actor(initialized), action.id, reason="not now")
    assert out.status == AgentActionStatus.REJECTED
    assert out.rejection_reason == "not now"


async def test_list_agent_actions_scoped(db: AsyncSession, initialized: SimpleNamespace) -> None:
    await _propose(db, initialized)
    actor = _user_actor(initialized)
    _, total_all = await service.list_agent_actions(db, actor, accessible_project_ids=None, params=PageParams())
    assert total_all == 1
    _, total_none = await service.list_agent_actions(db, actor, accessible_project_ids=set(), params=PageParams())
    assert total_none == 0
