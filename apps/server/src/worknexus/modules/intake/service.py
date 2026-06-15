"""intake service: request pool + triage state machine + accept-and-convert.

Single write entry for the intake domain (REST router, MCP tools, and the workchat
AgentAction dispatcher all call in here). State machine (v0.1):

  new / triaging / snoozed  --accept-->         converted   (creates a WorkItem)
                            --reject-->          rejected
                            --mark-duplicate-->  duplicate
  new / triaging            --snooze-->          snoozed
  snoozed (snooze_until passed, lazy on read) --> new

`converted / rejected / duplicate` are terminal; acting on them raises INTAKE_NOT_ACTIONABLE.
Rule-based triage suggestions are advisory only (decision A) — stored for display and to
prefill the convert form, never auto-applied. Provenance to the converted work item is
`WorkItem.source=intake` + `source_ref_id` + `converted_work_item_id` + audit (decision E).
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.config import get_settings
from worknexus.core.access import ScopeType, SubjectType
from worknexus.core.deps import Actor, ActorType
from worknexus.core.errors import BizError, ErrorCode
from worknexus.core.pagination import PageParams
from worknexus.modules.audit import service as audit
from worknexus.modules.audit.service import AuditAction
from worknexus.modules.identity.models import ProjectMember, RoleBinding, User
from worknexus.modules.intake.models import IntakeRequest
from worknexus.modules.intake.schemas import (
    ACTIONABLE_STATUSES,
    TERMINAL_STATUSES,
    IntakeAcceptIn,
    IntakeCreateIn,
    IntakeMetrics,
    IntakeOut,
    IntakeSource,
    IntakeStatus,
    IntakeUpdateIn,
)
from worknexus.modules.intake.triage import TriageSuggestion, get_triage_engine
from worknexus.modules.projects import service as projects_service
from worknexus.modules.projects.schemas import UserBriefOut
from worknexus.modules.work_items import service as work_items_service
from worknexus.modules.work_items.models import WorkItem
from worknexus.modules.work_items.schemas import WorkItemCreateIn, WorkItemPriority, WorkItemSource, WorkItemType


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


# --- triage suggestions ----------------------------------------------------------


async def _is_project_member(db: AsyncSession, tenant_id: str, project_id: str, user_id: str) -> bool:
    user = await db.get(User, user_id)
    if user is None or user.tenant_id != tenant_id:
        return False
    tenant_role = (
        await db.execute(
            select(RoleBinding.id).where(
                RoleBinding.subject_type == SubjectType.USER,
                RoleBinding.subject_id == user_id,
                RoleBinding.scope_type == ScopeType.TENANT,
            )
        )
    ).first()
    if tenant_role is not None:
        return True
    membership = (
        await db.execute(
            select(ProjectMember.id).where(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
        )
    ).first()
    return membership is not None


async def _run_triage(
    db: AsyncSession, tenant_id: str, project_id: str, title: str, description: str | None
) -> TriageSuggestion:
    suggestion = await get_triage_engine(get_settings()).suggest(
        db, project_id=project_id, tenant_id=tenant_id, title=title, description=description
    )
    # Server-side guard: a suggested assignee must be a current project member, else drop it
    # (advisory — never raise; rules don't guess people but a future provider might).
    if suggestion.suggested_assignee_id is not None and not await _is_project_member(
        db, tenant_id, project_id, suggestion.suggested_assignee_id
    ):
        suggestion = suggestion.model_copy(update={"suggested_assignee_id": None})
    return suggestion


def _triage_meta(suggestion: TriageSuggestion) -> dict[str, Any]:
    return {
        "provider": suggestion.provider,
        "version": suggestion.version,
        "reason": suggestion.reason,
        "confidence": suggestion.confidence,
        "generatedAt": _now().isoformat(),
    }


def _apply_suggestion(row: IntakeRequest, suggestion: TriageSuggestion) -> None:
    row.ai_summary = suggestion.summary
    row.ai_category = suggestion.category
    row.suggested_type = suggestion.suggested_type.value if suggestion.suggested_type else None
    row.suggested_priority = suggestion.suggested_priority.value if suggestion.suggested_priority else None
    row.suggested_assignee_id = suggestion.suggested_assignee_id
    row.triage_meta = _triage_meta(suggestion)


# --- output assembly -------------------------------------------------------------


def _to_out(row: IntakeRequest, assignee: User | None) -> IntakeOut:
    return IntakeOut(
        id=row.id,
        project_id=row.project_id,
        title=row.title,
        description=row.description,
        source=IntakeSource(row.source),
        source_ref_id=row.source_ref_id,
        status=IntakeStatus(row.status),
        submitter_id=row.submitter_id,
        ai_summary=row.ai_summary,
        ai_category=row.ai_category,
        suggested_type=WorkItemType(row.suggested_type) if row.suggested_type else None,
        suggested_priority=WorkItemPriority(row.suggested_priority) if row.suggested_priority else None,
        suggested_assignee_id=row.suggested_assignee_id,
        suggested_assignee=UserBriefOut.model_validate(assignee) if assignee is not None else None,
        triage_meta=dict(row.triage_meta) if row.triage_meta else None,
        duplicate_work_item_id=row.duplicate_work_item_id,
        converted_work_item_id=row.converted_work_item_id,
        snooze_until=row.snooze_until,
        rejection_reason=row.rejection_reason,
        created_by=row.created_by,
        updated_by=row.updated_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def _build_intake_outs(db: AsyncSession, rows: list[IntakeRequest]) -> list[IntakeOut]:
    if not rows:
        return []
    user_ids = {r.suggested_assignee_id for r in rows if r.suggested_assignee_id}
    users: dict[str, User] = {}
    if user_ids:
        found = (await db.execute(select(User).where(User.id.in_(user_ids)))).scalars().all()
        users = {u.id: u for u in found}
    return [_to_out(r, users.get(r.suggested_assignee_id) if r.suggested_assignee_id else None) for r in rows]


# --- row access + guards ---------------------------------------------------------


async def _get_intake_row(db: AsyncSession, actor: Actor, intake_id: str) -> IntakeRequest:
    row = await db.get(IntakeRequest, intake_id)
    if row is None or row.tenant_id != actor.tenant_id or row.deleted_at is not None:
        raise BizError(ErrorCode.INTAKE_NOT_FOUND, "intake request not found")
    return row


async def _maybe_unsnooze(db: AsyncSession, row: IntakeRequest) -> None:
    if row.status == IntakeStatus.SNOOZED and row.snooze_until is not None and _aware(row.snooze_until) <= _now():
        row.status = IntakeStatus.NEW
        row.snooze_until = None
        await db.commit()
        await db.refresh(row)


def _ensure_actionable(row: IntakeRequest) -> None:
    if IntakeStatus(row.status) in TERMINAL_STATUSES:
        raise BizError(ErrorCode.INTAKE_NOT_ACTIONABLE, f"intake request is already {row.status}")


# --- M7 dashboard metrics (read-only; owned here so the口径 stays in the intake domain) ----


async def get_project_intake_metrics(db: AsyncSession, actor: Actor, project_id: str) -> IntakeMetrics:
    """Intake counts for the project dashboard. Expired snoozes are virtually counted as
    `new` (read-time semantics, no row mutation), matching `_maybe_unsnooze`."""
    await projects_service.get_project(db, project_id, actor.tenant_id)
    effective_status = case(
        (
            and_(
                IntakeRequest.status == IntakeStatus.SNOOZED,
                IntakeRequest.snooze_until.is_not(None),
                IntakeRequest.snooze_until <= _now(),
            ),
            IntakeStatus.NEW.value,
        ),
        else_=IntakeRequest.status,
    )
    rows = (
        await db.execute(
            select(effective_status, func.count())
            .where(
                IntakeRequest.tenant_id == actor.tenant_id,
                IntakeRequest.project_id == project_id,
                IntakeRequest.deleted_at.is_(None),
            )
            .group_by(effective_status)
        )
    ).all()
    status_counts = {str(s): 0 for s in IntakeStatus}
    for status, count in rows:
        status_counts[str(status)] = count
    request_count = sum(status_counts.values())
    converted_count = status_counts[IntakeStatus.CONVERTED]
    conversion_rate = round(converted_count / request_count, 4) if request_count else 0.0
    return IntakeMetrics(
        request_count=request_count,
        status_counts=status_counts,
        converted_count=converted_count,
        conversion_rate=conversion_rate,
    )


# --- create / read ---------------------------------------------------------------


async def create_intake_request(
    db: AsyncSession,
    actor: Actor,
    project_id: str,
    data: IntakeCreateIn,
    *,
    source: IntakeSource = IntakeSource.MANUAL,
    source_ref_id: str | None = None,
    submitter_id: str | None = None,
) -> IntakeOut:
    await projects_service.get_project(db, project_id, actor.tenant_id)
    suggestion = await _run_triage(db, actor.tenant_id, project_id, data.title, data.description)
    submitter = submitter_id if submitter_id is not None else (actor.id if actor.type == ActorType.USER else None)
    row = IntakeRequest(
        tenant_id=actor.tenant_id,
        project_id=project_id,
        title=data.title,
        description=data.description,
        source=source,
        source_ref_id=source_ref_id,
        status=IntakeStatus.NEW,
        submitter_id=submitter,
        created_by=actor.id,
        updated_by=actor.id,
    )
    _apply_suggestion(row, suggestion)
    db.add(row)
    await db.flush()
    await audit.record(
        db,
        actor,
        action=AuditAction.INTAKE_CREATE,
        resource_type="intake_request",
        resource_id=row.id,
        project_id=project_id,
        after={"title": row.title, "source": row.source, "status": row.status},
    )
    await db.commit()
    return (await _build_intake_outs(db, [row]))[0]


async def list_intake_requests(
    db: AsyncSession,
    actor: Actor,
    project_id: str,
    *,
    status: IntakeStatus | None = None,
    source: IntakeSource | None = None,
    params: PageParams,
) -> tuple[list[IntakeOut], int]:
    await projects_service.get_project(db, project_id, actor.tenant_id)
    base = select(IntakeRequest).where(
        IntakeRequest.tenant_id == actor.tenant_id,
        IntakeRequest.project_id == project_id,
        IntakeRequest.deleted_at.is_(None),
    )
    if status is not None:
        base = base.where(IntakeRequest.status == status)
    if source is not None:
        base = base.where(IntakeRequest.source == source)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (
        (await db.execute(base.order_by(IntakeRequest.created_at.desc()).offset(params.offset).limit(params.page_size)))
        .scalars()
        .all()
    )
    return await _build_intake_outs(db, list(rows)), total


async def list_pending_intake(
    db: AsyncSession, actor: Actor, *, project_ids: set[str] | None, limit: int
) -> tuple[list[IntakeOut], int]:
    """Home: actionable (non-terminal) intake across the caller's projects. project_ids=None
    means all tenant projects (owner/admin); an empty set means no access. Read-only — no
    snooze mutation (snoozed items are actionable whether or not they have expired)."""
    if project_ids is not None and not project_ids:
        return [], 0
    base = select(IntakeRequest).where(
        IntakeRequest.tenant_id == actor.tenant_id,
        IntakeRequest.deleted_at.is_(None),
        IntakeRequest.status.in_(ACTIONABLE_STATUSES),
    )
    if project_ids is not None:
        base = base.where(IntakeRequest.project_id.in_(project_ids))
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (await db.execute(base.order_by(IntakeRequest.created_at.desc()).limit(limit))).scalars().all()
    return await _build_intake_outs(db, list(rows)), total


async def get_intake_request(db: AsyncSession, actor: Actor, intake_id: str) -> IntakeOut:
    row = await _get_intake_row(db, actor, intake_id)
    await _maybe_unsnooze(db, row)
    return (await _build_intake_outs(db, [row]))[0]


# --- triage actions --------------------------------------------------------------


async def update_intake_request(db: AsyncSession, actor: Actor, intake_id: str, data: IntakeUpdateIn) -> IntakeOut:
    row = await _get_intake_row(db, actor, intake_id)
    await _maybe_unsnooze(db, row)
    _ensure_actionable(row)
    before = {"title": row.title, "status": row.status}
    text_changed = False
    if data.title is not None and data.title != row.title:
        row.title = data.title
        text_changed = True
    if data.description is not None and data.description != row.description:
        row.description = data.description
        text_changed = True
    if data.status is not None:
        if data.status not in (IntakeStatus.NEW, IntakeStatus.TRIAGING):
            raise BizError(ErrorCode.INVALID_INPUT, "status can only be set to new or triaging via PATCH")
        row.status = data.status
    if text_changed:
        suggestion = await _run_triage(db, actor.tenant_id, row.project_id, row.title, row.description)
        _apply_suggestion(row, suggestion)
    row.updated_by = actor.id
    await audit.record(
        db,
        actor,
        action=AuditAction.INTAKE_UPDATE,
        resource_type="intake_request",
        resource_id=row.id,
        project_id=row.project_id,
        before=before,
        after={"title": row.title, "status": row.status},
    )
    await db.commit()
    return (await _build_intake_outs(db, [row]))[0]


async def accept_intake_request(
    db: AsyncSession,
    actor: Actor,
    intake_id: str,
    data: IntakeAcceptIn,
    *,
    reporter_id: str | None = None,
) -> IntakeOut:
    """Accept-and-convert in a single transaction (decision C): create the work item
    (commit-free core), backfill the conversion, set status=converted, then commit once.

    `reporter_id` must resolve to a real user (the work item's reporter is a users FK). For a
    human triager `actor` is that user; the AgentAction dispatcher passes the requesting user."""
    row = await _get_intake_row(db, actor, intake_id)
    await _maybe_unsnooze(db, row)
    _ensure_actionable(row)

    effective_reporter = row.submitter_id or reporter_id or (actor.id if actor.type == ActorType.USER else None)
    if effective_reporter is None:
        raise BizError(ErrorCode.INVALID_INPUT, "cannot determine a reporter user for the converted work item")

    work_data = WorkItemCreateIn(
        type=data.type or (WorkItemType(row.suggested_type) if row.suggested_type else WorkItemType.TASK),
        title=data.title or row.title,
        description=row.description,
        priority=data.priority
        or (WorkItemPriority(row.suggested_priority) if row.suggested_priority else WorkItemPriority.MEDIUM),
        assignee_id=data.assignee_id or row.suggested_assignee_id,
    )
    item = await work_items_service.create_work_item_in_tx(
        db,
        actor,
        row.project_id,
        work_data,
        source=WorkItemSource.INTAKE,
        source_ref_id=row.id,
        reporter_id=effective_reporter,
    )
    row.converted_work_item_id = item.id
    row.status = IntakeStatus.CONVERTED
    row.updated_by = actor.id
    await audit.record(
        db,
        actor,
        action=AuditAction.INTAKE_ACCEPT,
        resource_type="intake_request",
        resource_id=row.id,
        project_id=row.project_id,
        after={"workItemId": item.id, "workItemKey": item.key},
    )
    await db.commit()
    return (await _build_intake_outs(db, [row]))[0]


async def reject_intake_request(db: AsyncSession, actor: Actor, intake_id: str, reason: str | None = None) -> IntakeOut:
    row = await _get_intake_row(db, actor, intake_id)
    await _maybe_unsnooze(db, row)
    _ensure_actionable(row)
    row.status = IntakeStatus.REJECTED
    row.rejection_reason = reason
    row.updated_by = actor.id
    await audit.record(
        db,
        actor,
        action=AuditAction.INTAKE_REJECT,
        resource_type="intake_request",
        resource_id=row.id,
        project_id=row.project_id,
        detail={"reason": reason},
    )
    await db.commit()
    return (await _build_intake_outs(db, [row]))[0]


async def mark_duplicate(db: AsyncSession, actor: Actor, intake_id: str, duplicate_work_item_id: str) -> IntakeOut:
    row = await _get_intake_row(db, actor, intake_id)
    await _maybe_unsnooze(db, row)
    _ensure_actionable(row)
    target = await db.get(WorkItem, duplicate_work_item_id)
    if (
        target is None
        or target.tenant_id != actor.tenant_id
        or target.deleted_at is not None
        or target.project_id != row.project_id
    ):
        raise BizError(
            ErrorCode.INTAKE_DUPLICATE_TARGET_INVALID, "duplicate target work item not found in this project"
        )
    row.status = IntakeStatus.DUPLICATE
    row.duplicate_work_item_id = duplicate_work_item_id
    row.updated_by = actor.id
    await audit.record(
        db,
        actor,
        action=AuditAction.INTAKE_MARK_DUPLICATE,
        resource_type="intake_request",
        resource_id=row.id,
        project_id=row.project_id,
        after={"duplicateWorkItemId": duplicate_work_item_id},
    )
    await db.commit()
    return (await _build_intake_outs(db, [row]))[0]


async def snooze_intake_request(db: AsyncSession, actor: Actor, intake_id: str, snooze_until: datetime) -> IntakeOut:
    row = await _get_intake_row(db, actor, intake_id)
    await _maybe_unsnooze(db, row)
    _ensure_actionable(row)
    if _aware(snooze_until) <= _now():
        raise BizError(ErrorCode.INVALID_INPUT, "snooze_until must be in the future")
    row.status = IntakeStatus.SNOOZED
    row.snooze_until = snooze_until
    row.updated_by = actor.id
    await audit.record(
        db,
        actor,
        action=AuditAction.INTAKE_SNOOZE,
        resource_type="intake_request",
        resource_id=row.id,
        project_id=row.project_id,
        after={"snoozeUntil": _aware(snooze_until).isoformat()},
    )
    await db.commit()
    return (await _build_intake_outs(db, [row]))[0]
