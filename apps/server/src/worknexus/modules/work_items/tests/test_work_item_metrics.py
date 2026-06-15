"""M7 dashboard domain metrics owned by work_items: distributions, overdue list,
workload, and the 7-day created/completed trends — on real (rolled-back) PostgreSQL."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.deps import Actor, ActorType
from worknexus.core.pagination import PageParams
from worknexus.modules.work_items import service
from worknexus.modules.work_items.schemas import (
    WorkItemCreateIn,
    WorkItemPriority,
    WorkItemSource,
    WorkItemStatus,
    WorkItemTransitionIn,
    WorkItemType,
)

pytestmark = [pytest.mark.integration, pytest.mark.p1]

# Linear forward path through the state machine to reach `done`.
_TO_DONE = [WorkItemStatus.TODO, WorkItemStatus.IN_PROGRESS, WorkItemStatus.REVIEW, WorkItemStatus.DONE]


def _actor(initialized: SimpleNamespace) -> Actor:
    return Actor(id=initialized.owner.id, type=ActorType.USER, tenant_id=initialized.tenant.id)


async def _create(
    db: AsyncSession,
    initialized: SimpleNamespace,
    *,
    type: WorkItemType = WorkItemType.TASK,
    title: str = "Item",
    priority: WorkItemPriority = WorkItemPriority.MEDIUM,
    source: WorkItemSource = WorkItemSource.MANUAL,
    due_at: datetime | None = None,
    assignee_id: str | None = None,
) -> str:
    out = await service.create_work_item(
        db,
        _actor(initialized),
        initialized.project.id,
        WorkItemCreateIn(type=type, title=title, priority=priority, due_at=due_at, assignee_id=assignee_id),
        source=source,
    )
    return out.id


async def _advance_to_done(db: AsyncSession, initialized: SimpleNamespace, item_id: str) -> None:
    for status in _TO_DONE:
        await service.transition_work_item(db, _actor(initialized), item_id, WorkItemTransitionIn(status=status))


async def test_metrics_distributions_and_counts(db: AsyncSession, initialized: SimpleNamespace) -> None:
    pid = initialized.project.id
    past = datetime.now(UTC) - timedelta(days=2)
    await _create(db, initialized, type=WorkItemType.BUG, priority=WorkItemPriority.URGENT, due_at=past)
    await _create(db, initialized, type=WorkItemType.TASK, priority=WorkItemPriority.HIGH)
    await _create(db, initialized, type=WorkItemType.TASK, source=WorkItemSource.AI_CHAT)
    await _create(db, initialized, type=WorkItemType.TASK, source=WorkItemSource.INTAKE)
    done_id = await _create(db, initialized, type=WorkItemType.TASK, priority=WorkItemPriority.URGENT, due_at=past)
    await _advance_to_done(db, initialized, done_id)

    m = await service.get_project_work_item_metrics(db, _actor(initialized), pid)

    assert m.total_count == 5
    # distributions are zero-filled over every enum value
    assert set(m.status_counts) == {str(s) for s in WorkItemStatus}
    assert set(m.type_counts) == {str(t) for t in WorkItemType}
    assert m.type_counts["bug"] == 1
    assert m.type_counts["task"] == 4
    assert m.status_counts["done"] == 1
    assert m.status_counts["backlog"] == 4
    assert m.source_counts["ai_chat"] == 1
    assert m.source_counts["intake"] == 1
    assert m.source_counts["manual"] == 3
    # high priority = urgent + high (both done and open count toward the distribution metric)
    assert m.high_priority_count == 3
    # overdue excludes the done item -> only the first urgent bug remains
    assert m.overdue_count == 1
    # ai-created keeps the M3 semantics: ai_chat + mcp, NOT intake
    assert m.ai_created_count == 1


async def test_metrics_trends_cover_seven_utc_days(db: AsyncSession, initialized: SimpleNamespace) -> None:
    await _create(db, initialized)
    await _create(db, initialized)
    done_id = await _create(db, initialized)
    await _advance_to_done(db, initialized, done_id)

    m = await service.get_project_work_item_metrics(db, _actor(initialized), initialized.project.id)

    assert len(m.created_trend) == 7
    assert len(m.completed_trend) == 7
    today = datetime.now(UTC).date().isoformat()
    assert m.created_trend[-1].date == today  # oldest first, today last
    assert m.created_trend[-1].count == 3
    assert m.completed_trend[-1].count == 1
    assert sum(p.count for p in m.created_trend) == 3


async def test_overdue_list_sorted_paginated(db: AsyncSession, initialized: SimpleNamespace) -> None:
    now = datetime.now(UTC)
    # most overdue + urgent should sort first
    await _create(
        db, initialized, title="old-urgent", priority=WorkItemPriority.URGENT, due_at=now - timedelta(days=10)
    )
    await _create(db, initialized, title="recent-low", priority=WorkItemPriority.LOW, due_at=now - timedelta(days=1))
    # not overdue (future) and a done-overdue are excluded
    await _create(db, initialized, title="future", due_at=now + timedelta(days=5))
    done_id = await _create(db, initialized, title="done-overdue", due_at=now - timedelta(days=3))
    await _advance_to_done(db, initialized, done_id)

    rows, total = await service.list_project_overdue_work_items(
        db, _actor(initialized), initialized.project.id, PageParams(page=1, page_size=1)
    )
    assert total == 2  # future + done excluded
    assert len(rows) == 1  # page_size honored
    assert rows[0].title == "old-urgent"
    assert rows[0].days_overdue == 10

    page2, _ = await service.list_project_overdue_work_items(
        db, _actor(initialized), initialized.project.id, PageParams(page=2, page_size=1)
    )
    assert page2[0].title == "recent-low"


async def test_workload_buckets(db: AsyncSession, initialized: SimpleNamespace) -> None:
    owner_id = initialized.owner.id
    await _create(db, initialized, assignee_id=owner_id, priority=WorkItemPriority.HIGH)
    await _create(db, initialized, assignee_id=owner_id, due_at=datetime.now(UTC) - timedelta(days=1))
    await _create(db, initialized)  # unassigned

    buckets = await service.get_project_workload_metrics(db, _actor(initialized), initialized.project.id)

    by_assignee = {b.assignee_id: b for b in buckets}
    assert by_assignee[owner_id].total_count == 2
    assert by_assignee[owner_id].high_priority_count == 1
    assert by_assignee[owner_id].overdue_count == 1
    assert by_assignee[owner_id].assignee is not None
    assert None in by_assignee  # unassigned bucket
    assert by_assignee[None].total_count == 1
    assert by_assignee[None].assignee is None
    # sorted by total_count desc
    assert buckets[0].total_count >= buckets[-1].total_count
