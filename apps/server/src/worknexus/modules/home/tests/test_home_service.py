"""home.service.get_home_snapshot: cross-project aggregation of the five cards and
accessible-project scoping (D6 — a user never sees other projects' work)."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.access import load_subject
from worknexus.core.deps import Actor, ActorType
from worknexus.modules.home import service
from worknexus.modules.identity.models import ProjectMember, User
from worknexus.modules.identity.schemas import DelegationContext
from worknexus.modules.intake import service as intake_service
from worknexus.modules.intake.schemas import IntakeCreateIn
from worknexus.modules.work_items import service as work_items_service
from worknexus.modules.work_items.schemas import WorkItemCreateIn, WorkItemOut, WorkItemSource, WorkItemType
from worknexus.modules.workchat import service as workchat_service

pytestmark = [pytest.mark.integration, pytest.mark.p1]


def _actor(init: SimpleNamespace, user_id: str | None = None) -> Actor:
    return Actor(id=user_id or init.owner.id, type=ActorType.USER, tenant_id=init.tenant.id)


async def _create_wi(
    db: AsyncSession,
    init: SimpleNamespace,
    actor: Actor,
    *,
    source: WorkItemSource = WorkItemSource.MANUAL,
    due_at: datetime | None = None,
    assignee_id: str | None = None,
    title: str = "Item",
) -> WorkItemOut:
    return await work_items_service.create_work_item(
        db,
        actor,
        init.project.id,
        WorkItemCreateIn(type=WorkItemType.TASK, title=title, assignee_id=assignee_id, due_at=due_at),
        source=source,
    )


async def _seed_pending_action(db: AsyncSession, init: SimpleNamespace) -> None:
    delegation = DelegationContext(
        tenant_id=init.tenant.id,
        user_id=init.owner.id,
        agent_id=init.agent.id,
        project_id=init.project.id,
        conversation_id=None,
        run_id=None,
        permissions_snapshot={"user": [], "agent": [], "effective": ["work_item.create"]},
    )
    await workchat_service.create_pending_agent_action(
        db,
        delegation,
        tool_name="workitem_create_work_item",
        arguments={"title": "AI proposed", "type": "task"},
        skill_invocation_id="si_home_0001",
    )


async def test_snapshot_aggregates_all_cards(db: AsyncSession, initialized: SimpleNamespace) -> None:
    actor = _actor(initialized)
    past = datetime.now(UTC) - timedelta(days=2)
    await _create_wi(db, initialized, actor, assignee_id=initialized.owner.id)  # open todo
    await _create_wi(db, initialized, actor, assignee_id=initialized.owner.id, due_at=past)  # todo + overdue
    await _create_wi(db, initialized, actor, source=WorkItemSource.AI_CHAT)  # recent AI-created (unassigned)
    await intake_service.create_intake_request(db, actor, initialized.project.id, IntakeCreateIn(title="intake"))
    await _seed_pending_action(db, initialized)

    snap = await service.get_home_snapshot(db, await load_subject(db, actor))

    assert snap.my_todos.total == 2 and len(snap.my_todos.items) == 2
    assert snap.overdue.total == 1 and snap.overdue.items[0].due_at is not None
    assert snap.recent_ai_created.total == 1 and snap.recent_ai_created.items[0].source == WorkItemSource.AI_CHAT
    assert snap.pending_agent_actions.total == 1
    assert snap.pending_intake.total == 1


async def test_member_without_projects_sees_empty(
    db: AsyncSession, initialized: SimpleNamespace, member_user: User
) -> None:
    await _create_wi(db, initialized, _actor(initialized), assignee_id=initialized.owner.id)
    await _seed_pending_action(db, initialized)

    snap = await service.get_home_snapshot(db, await load_subject(db, _actor(initialized, member_user.id)))

    assert snap.my_todos.total == 0
    assert snap.overdue.total == 0
    assert snap.recent_ai_created.total == 0
    assert snap.pending_agent_actions.total == 0
    assert snap.pending_intake.total == 0


async def test_member_sees_only_their_assigned_work(
    db: AsyncSession, initialized: SimpleNamespace, member_user: User
) -> None:
    owner_actor = _actor(initialized)
    await _create_wi(db, initialized, owner_actor, assignee_id=initialized.owner.id, title="owner's")
    db.add(
        ProjectMember(
            tenant_id=initialized.tenant.id,
            project_id=initialized.project.id,
            user_id=member_user.id,
            role="member",
            created_by=initialized.owner.id,
        )
    )
    await db.flush()
    await _create_wi(db, initialized, owner_actor, assignee_id=member_user.id, title="member's")

    snap = await service.get_home_snapshot(db, await load_subject(db, _actor(initialized, member_user.id)))

    assert snap.my_todos.total == 1
    assert snap.my_todos.items[0].assignee_id == member_user.id
