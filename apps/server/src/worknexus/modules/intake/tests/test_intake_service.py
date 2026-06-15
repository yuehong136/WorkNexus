"""intake service: triage on create, the triage state machine, and the atomic
accept-and-convert path, on a real (rolled-back) PostgreSQL session."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.deps import Actor, ActorType
from worknexus.core.errors import BizError, ErrorCode
from worknexus.core.pagination import PageParams
from worknexus.modules.audit.models import AuditLog
from worknexus.modules.audit.service import AuditAction
from worknexus.modules.intake import service
from worknexus.modules.intake.models import IntakeRequest
from worknexus.modules.intake.schemas import (
    IntakeAcceptIn,
    IntakeCreateIn,
    IntakeSource,
    IntakeStatus,
    IntakeUpdateIn,
)
from worknexus.modules.work_items import service as work_items_service
from worknexus.modules.work_items.models import WorkItem
from worknexus.modules.work_items.schemas import WorkItemCreateIn, WorkItemPriority, WorkItemSource, WorkItemType

pytestmark = pytest.mark.p1


def _actor(initialized: SimpleNamespace) -> Actor:
    return Actor(id=initialized.owner.id, type=ActorType.USER, tenant_id=initialized.tenant.id)


async def _create(
    db: AsyncSession,
    initialized: SimpleNamespace,
    *,
    title: str = "Login crash",
    description: str | None = "The app crashes on login, urgent",
) -> str:
    out = await service.create_intake_request(
        db, _actor(initialized), initialized.project.id, IntakeCreateIn(title=title, description=description)
    )
    return out.id


async def test_create_runs_triage_and_audits(db: AsyncSession, initialized: SimpleNamespace) -> None:
    out = await service.create_intake_request(
        db,
        _actor(initialized),
        initialized.project.id,
        IntakeCreateIn(title="Login crash", description="The app crashes on login, urgent"),
    )
    assert out.status == IntakeStatus.NEW
    assert out.source == IntakeSource.MANUAL
    assert out.submitter_id == initialized.owner.id
    assert out.suggested_type == WorkItemType.BUG
    assert out.suggested_priority == WorkItemPriority.URGENT
    assert out.ai_summary
    assert out.triage_meta is not None and out.triage_meta["provider"] == "rules"
    assert "generatedAt" in out.triage_meta

    rows = (
        (
            await db.execute(
                select(AuditLog).where(AuditLog.action == AuditAction.INTAKE_CREATE, AuditLog.resource_id == out.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1


async def test_accept_converts_atomically(db: AsyncSession, initialized: SimpleNamespace) -> None:
    intake_id = await _create(db, initialized)
    out = await service.accept_intake_request(db, _actor(initialized), intake_id, IntakeAcceptIn())

    assert out.status == IntakeStatus.CONVERTED
    assert out.converted_work_item_id is not None
    work_item = await db.get(WorkItem, out.converted_work_item_id)
    assert work_item is not None
    assert work_item.source == WorkItemSource.INTAKE
    assert work_item.source_ref_id == intake_id
    assert work_item.reporter_id == initialized.owner.id
    # Provenance is carried by source fields; the triage suggestion drove the type.
    assert work_item.type == WorkItemType.BUG

    assert (
        await db.execute(
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.action == AuditAction.INTAKE_ACCEPT, AuditLog.resource_id == intake_id)
        )
    ).scalar_one() == 1


async def test_accept_applies_overrides(db: AsyncSession, initialized: SimpleNamespace) -> None:
    intake_id = await _create(db, initialized)
    out = await service.accept_intake_request(
        db,
        _actor(initialized),
        intake_id,
        IntakeAcceptIn(type=WorkItemType.REQUIREMENT, priority=WorkItemPriority.LOW, title="Overridden title"),
    )
    work_item = await db.get(WorkItem, out.converted_work_item_id)
    assert work_item is not None
    assert work_item.type == WorkItemType.REQUIREMENT
    assert work_item.priority == WorkItemPriority.LOW
    assert work_item.title == "Overridden title"


async def test_double_accept_is_not_actionable(db: AsyncSession, initialized: SimpleNamespace) -> None:
    intake_id = await _create(db, initialized)
    await service.accept_intake_request(db, _actor(initialized), intake_id, IntakeAcceptIn())
    with pytest.raises(BizError) as exc:
        await service.accept_intake_request(db, _actor(initialized), intake_id, IntakeAcceptIn())
    assert exc.value.code == ErrorCode.INTAKE_NOT_ACTIONABLE


async def test_reject(db: AsyncSession, initialized: SimpleNamespace) -> None:
    intake_id = await _create(db, initialized)
    out = await service.reject_intake_request(db, _actor(initialized), intake_id, reason="not relevant")
    assert out.status == IntakeStatus.REJECTED
    assert out.rejection_reason == "not relevant"
    with pytest.raises(BizError):
        await service.reject_intake_request(db, _actor(initialized), intake_id)


async def test_mark_duplicate_valid_and_invalid(db: AsyncSession, initialized: SimpleNamespace) -> None:
    actor = _actor(initialized)
    target = await work_items_service.create_work_item(
        db, actor, initialized.project.id, WorkItemCreateIn(type=WorkItemType.BUG, title="Existing bug")
    )
    intake_id = await _create(db, initialized)
    out = await service.mark_duplicate(db, actor, intake_id, target.id)
    assert out.status == IntakeStatus.DUPLICATE
    assert out.duplicate_work_item_id == target.id

    other = await _create(db, initialized)
    with pytest.raises(BizError) as exc:
        await service.mark_duplicate(db, actor, other, "missing_work_item_id")
    assert exc.value.code == ErrorCode.INTAKE_DUPLICATE_TARGET_INVALID


async def test_snooze_then_lazy_unsnooze(db: AsyncSession, initialized: SimpleNamespace) -> None:
    actor = _actor(initialized)
    intake_id = await _create(db, initialized)
    out = await service.snooze_intake_request(db, actor, intake_id, datetime.now(UTC) + timedelta(days=1))
    assert out.status == IntakeStatus.SNOOZED
    assert out.snooze_until is not None

    # Force the snooze into the past, then a read lazily un-snoozes back to new.
    row = await db.get(IntakeRequest, intake_id)
    assert row is not None
    row.snooze_until = datetime.now(UTC) - timedelta(minutes=1)
    await db.commit()
    refreshed = await service.get_intake_request(db, actor, intake_id)
    assert refreshed.status == IntakeStatus.NEW
    assert refreshed.snooze_until is None


async def test_snooze_past_is_rejected(db: AsyncSession, initialized: SimpleNamespace) -> None:
    intake_id = await _create(db, initialized)
    with pytest.raises(BizError) as exc:
        await service.snooze_intake_request(
            db, _actor(initialized), intake_id, datetime.now(UTC) - timedelta(minutes=1)
        )
    assert exc.value.code == ErrorCode.INVALID_INPUT


async def test_update_recomputes_suggestion(db: AsyncSession, initialized: SimpleNamespace) -> None:
    actor = _actor(initialized)
    intake_id = await _create(db, initialized, title="Crash", description="app crashes")
    before = await service.get_intake_request(db, actor, intake_id)
    assert before.suggested_type == WorkItemType.BUG

    out = await service.update_intake_request(
        db,
        actor,
        intake_id,
        IntakeUpdateIn(title="Feature request", description="please add a new feature", status=IntakeStatus.TRIAGING),
    )
    assert out.status == IntakeStatus.TRIAGING
    assert out.suggested_type == WorkItemType.REQUIREMENT


async def test_list_filters_by_status_and_source(db: AsyncSession, initialized: SimpleNamespace) -> None:
    actor = _actor(initialized)
    a = await _create(db, initialized, title="One")
    await _create(db, initialized, title="Two")
    await service.reject_intake_request(db, actor, a)

    items, total = await service.list_intake_requests(
        db, actor, initialized.project.id, status=IntakeStatus.NEW, params=PageParams(page=1, page_size=20)
    )
    assert total == 1
    assert all(i.status == IntakeStatus.NEW for i in items)

    _items, total_all = await service.list_intake_requests(
        db, actor, initialized.project.id, source=IntakeSource.MANUAL, params=PageParams(page=1, page_size=20)
    )
    assert total_all == 2


async def test_get_unknown_raises_not_found(db: AsyncSession, initialized: SimpleNamespace) -> None:
    with pytest.raises(BizError) as exc:
        await service.get_intake_request(db, _actor(initialized), "missing_id")
    assert exc.value.code == ErrorCode.INTAKE_NOT_FOUND


async def test_ai_actor_accept_requires_reporter(db: AsyncSession, initialized: SimpleNamespace) -> None:
    """An AI-agent actor accept with no submitter and no reporter override cannot resolve a
    users-FK reporter — guard rejects rather than violating the FK."""
    intake_id = await _create(db, initialized, description="plain text")
    # Strip the submitter so there is no user to attribute the work item to.
    row = await db.get(IntakeRequest, intake_id)
    assert row is not None
    row.submitter_id = None
    await db.commit()

    ai_actor = Actor(id=initialized.agent.id, type=ActorType.AI_AGENT, tenant_id=initialized.tenant.id)
    with pytest.raises(BizError) as exc:
        await service.accept_intake_request(db, ai_actor, intake_id, IntakeAcceptIn())
    assert exc.value.code == ErrorCode.INVALID_INPUT

    # With an explicit reporter (as the AgentAction dispatcher passes), the accept succeeds.
    out = await service.accept_intake_request(
        db, ai_actor, intake_id, IntakeAcceptIn(), reporter_id=initialized.owner.id
    )
    assert out.status == IntakeStatus.CONVERTED
    work_item = await db.get(WorkItem, out.converted_work_item_id)
    assert work_item is not None and work_item.reporter_id == initialized.owner.id
