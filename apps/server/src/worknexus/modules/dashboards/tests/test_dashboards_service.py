"""dashboards service: orchestration of work_items + intake metrics into the four DTOs."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.deps import Actor, ActorType
from worknexus.core.pagination import PageParams
from worknexus.modules.dashboards import service
from worknexus.modules.intake import service as intake_service
from worknexus.modules.intake.schemas import IntakeCreateIn
from worknexus.modules.work_items import service as work_items_service
from worknexus.modules.work_items.schemas import WorkItemCreateIn, WorkItemPriority, WorkItemSource, WorkItemType

pytestmark = [pytest.mark.integration, pytest.mark.p1]


def _actor(initialized: SimpleNamespace) -> Actor:
    return Actor(id=initialized.owner.id, type=ActorType.USER, tenant_id=initialized.tenant.id)


async def _seed(db: AsyncSession, initialized: SimpleNamespace) -> None:
    actor, pid = _actor(initialized), initialized.project.id
    past = datetime.now(UTC) - timedelta(days=2)
    await work_items_service.create_work_item(
        db,
        actor,
        pid,
        WorkItemCreateIn(type=WorkItemType.BUG, title="overdue", priority=WorkItemPriority.URGENT, due_at=past),
    )
    await work_items_service.create_work_item(
        db, actor, pid, WorkItemCreateIn(type=WorkItemType.TASK, title="ai"), source=WorkItemSource.AI_CHAT
    )
    await intake_service.create_intake_request(db, actor, pid, IntakeCreateIn(title="lead", description=None))


async def test_summary_combines_work_items_and_intake(db: AsyncSession, initialized: SimpleNamespace) -> None:
    await _seed(db, initialized)
    summary = await service.get_dashboard_summary(db, _actor(initialized), initialized.project.id)
    assert summary.total_count == 2
    assert summary.ai_created_count == 1
    assert summary.overdue_count == 1
    assert summary.source_counts["ai_chat"] == 1
    assert summary.intake_request_count == 1
    assert summary.intake_converted_count == 0
    assert len(summary.created_trend) == 7
    assert len(summary.completed_trend) == 7


async def test_workload_and_overdue(db: AsyncSession, initialized: SimpleNamespace) -> None:
    await _seed(db, initialized)
    workload = await service.get_dashboard_workload(db, _actor(initialized), initialized.project.id)
    assert workload.items  # at least the unassigned bucket

    page = await service.get_dashboard_overdue(
        db, _actor(initialized), initialized.project.id, PageParams(page=1, page_size=20)
    )
    assert page.total == 1
    assert page.items[0].days_overdue == 2


async def test_insights_carry_provenance(db: AsyncSession, initialized: SimpleNamespace) -> None:
    await _seed(db, initialized)
    out = await service.get_dashboard_insights(db, _actor(initialized), initialized.project.id)
    assert out.provenance.provider == "rules"
    assert out.provenance.version == "1"
    assert out.provenance.generated_at is not None
    # the seeded overdue + urgent item triggers overdue + high_priority + risk signals
    kinds = {i.kind for i in out.insights}
    assert "overdue" in kinds


async def test_snapshot_bundles_and_caps_overdue(db: AsyncSession, initialized: SimpleNamespace) -> None:
    actor, pid = _actor(initialized), initialized.project.id
    past = datetime.now(UTC) - timedelta(days=3)
    for i in range(3):
        await work_items_service.create_work_item(
            db, actor, pid, WorkItemCreateIn(type=WorkItemType.TASK, title=f"late-{i}", due_at=past)
        )

    snapshot = await service.get_project_dashboard_snapshot(db, actor, pid, overdue_limit=2)

    assert snapshot.summary.total_count == 3
    assert snapshot.overdue_count == 3  # full count
    assert len(snapshot.overdue_preview) == 2  # capped by overdue_limit
    assert snapshot.insights.provenance.provider == "rules"
    assert snapshot.workload  # at least the unassigned bucket
