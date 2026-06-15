from collections.abc import Sequence
from datetime import UTC, date, datetime, time, timedelta
from enum import StrEnum
from typing import Any

from pydantic import ValidationError
from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.access import ScopeType, SubjectType
from worknexus.core.deps import Actor, ActorType
from worknexus.core.errors import BizError, ErrorCode
from worknexus.core.pagination import PageParams
from worknexus.modules.audit import service as audit
from worknexus.modules.audit.service import AuditAction
from worknexus.modules.identity.models import ProjectMember, RoleBinding, User
from worknexus.modules.projects import service as projects_service
from worknexus.modules.projects.models import Project
from worknexus.modules.projects.schemas import ProjectStatus, UserBriefOut
from worknexus.modules.work_items.models import WorkItem, WorkItemActivity, WorkItemComment, WorkItemRelation
from worknexus.modules.work_items.schemas import (
    ALLOWED_TRANSITIONS,
    CUSTOM_FIELD_SCHEMAS,
    MANUAL_RELATION_TYPES,
    ActivityAction,
    ActivityOut,
    CommentAuthorType,
    CommentCreateIn,
    CommentOut,
    DailyCount,
    OverdueWorkItem,
    ProjectActivityOut,
    ProjectSummaryOut,
    RelationCreateIn,
    RelationDirection,
    RelationOut,
    RelationType,
    WorkItemBriefOut,
    WorkItemCreateIn,
    WorkItemMetrics,
    WorkItemOut,
    WorkItemPriority,
    WorkItemSort,
    WorkItemSource,
    WorkItemStatus,
    WorkItemTransitionIn,
    WorkItemType,
    WorkItemUpdateIn,
    WorkloadBucket,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def validate_custom_fields(item_type: WorkItemType, data: dict[str, Any]) -> dict[str, Any]:
    """Per-type light validation (decision B): reject unknown keys / wrong base types.

    Shared by REST and MCP/AI write paths so no surface can pollute custom_fields."""
    model = CUSTOM_FIELD_SCHEMAS[item_type]
    try:
        validated = model.model_validate(data)
    except ValidationError as exc:
        raise BizError(ErrorCode.INVALID_CUSTOM_FIELDS, "invalid custom fields for this work item type") from exc
    return validated.model_dump(exclude_none=True)


async def ensure_project_writable(db: AsyncSession, project_id: str, tenant_id: str) -> Project:
    """Load the parent project and block writes on archived (read-only) projects."""
    project = await db.get(Project, project_id)
    if project is None or project.tenant_id != tenant_id:
        raise BizError(ErrorCode.PROJECT_NOT_FOUND, "project not found")
    if project.status != ProjectStatus.ACTIVE:
        raise BizError(ErrorCode.PROJECT_ARCHIVED, "project is archived")
    return project


async def _ensure_assignable(db: AsyncSession, tenant_id: str, project_id: str, user_id: str) -> None:
    """Assignee/reporter must exist, be in this tenant, and have access to the project
    (tenant role grants global access, otherwise an explicit project membership)."""
    user = await db.get(User, user_id)
    if user is None or user.tenant_id != tenant_id:
        raise BizError(ErrorCode.INVALID_ASSIGNEE, "assignee is not a valid user")
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
        return
    membership = (
        await db.execute(
            select(ProjectMember.id).where(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
        )
    ).first()
    if membership is None:
        raise BizError(ErrorCode.INVALID_ASSIGNEE, "assignee has no access to this project")


async def _next_seq(db: AsyncSession, project_id: str) -> int:
    """Atomically mint the next per-project sequence. The single UPDATE row-locks the
    project row, so concurrent inserts serialize per project without scanning work_items."""
    result = await db.execute(
        update(Project)
        .where(Project.id == project_id)
        .values(work_item_seq=Project.work_item_seq + 1)
        .returning(Project.work_item_seq)
    )
    return result.scalar_one()


async def _record_activity(
    db: AsyncSession,
    actor: Actor,
    work_item_id: str,
    action: ActivityAction,
    *,
    field: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> None:
    db.add(
        WorkItemActivity(
            tenant_id=actor.tenant_id,
            work_item_id=work_item_id,
            actor_type=actor.type,
            actor_id=actor.id,
            action=action,
            field=field,
            before=before,
            after=after,
        )
    )
    await db.flush()


async def get_work_item(db: AsyncSession, work_item_id: str, tenant_id: str) -> WorkItem:
    item = await db.get(WorkItem, work_item_id)
    if item is None or item.tenant_id != tenant_id or item.deleted_at is not None:
        raise BizError(ErrorCode.WORK_ITEM_NOT_FOUND, "work item not found")
    return item


def _to_out(item: WorkItem, assignee: User | None) -> WorkItemOut:
    return WorkItemOut(
        id=item.id,
        key=item.key,
        project_id=item.project_id,
        seq=item.seq,
        type=WorkItemType(item.type),
        title=item.title,
        description=item.description,
        status=WorkItemStatus(item.status),
        priority=WorkItemPriority(item.priority),
        assignee_id=item.assignee_id,
        assignee=UserBriefOut.model_validate(assignee) if assignee is not None else None,
        reporter_id=item.reporter_id,
        due_at=item.due_at,
        tags=list(item.tags or []),
        source=WorkItemSource(item.source),
        source_ref_id=item.source_ref_id,
        ai_summary=item.ai_summary,
        acceptance_criteria=item.acceptance_criteria,
        custom_fields=dict(item.custom_fields or {}),
        created_by=item.created_by,
        updated_by=item.updated_by,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


async def _build_work_item_outs(db: AsyncSession, items: list[WorkItem]) -> list[WorkItemOut]:
    if not items:
        return []
    user_ids = {i.assignee_id for i in items if i.assignee_id}
    users: dict[str, User] = {}
    if user_ids:
        rows = (await db.execute(select(User).where(User.id.in_(user_ids)))).scalars().all()
        users = {u.id: u for u in rows}
    return [_to_out(i, users.get(i.assignee_id) if i.assignee_id else None) for i in items]


_SORT_ORDER = {
    WorkItemSort.CREATED_DESC: WorkItem.created_at.desc(),
    WorkItemSort.CREATED_ASC: WorkItem.created_at.asc(),
    WorkItemSort.UPDATED_DESC: WorkItem.updated_at.desc(),
    WorkItemSort.UPDATED_ASC: WorkItem.updated_at.asc(),
}


async def list_work_items(
    db: AsyncSession,
    actor: Actor,
    project_id: str,
    *,
    status: WorkItemStatus | None = None,
    type: WorkItemType | None = None,
    priority: WorkItemPriority | None = None,
    assignee_id: str | None = None,
    sort: WorkItemSort = WorkItemSort.CREATED_DESC,
    params: PageParams,
) -> tuple[list[WorkItemOut], int]:
    await projects_service.get_project(db, project_id, actor.tenant_id)
    base = select(WorkItem).where(
        WorkItem.tenant_id == actor.tenant_id,
        WorkItem.project_id == project_id,
        WorkItem.deleted_at.is_(None),
    )
    if status is not None:
        base = base.where(WorkItem.status == status)
    if type is not None:
        base = base.where(WorkItem.type == type)
    if priority is not None:
        base = base.where(WorkItem.priority == priority)
    if assignee_id is not None:
        base = base.where(WorkItem.assignee_id == assignee_id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    items = (
        (await db.execute(base.order_by(_SORT_ORDER[sort]).offset(params.offset).limit(params.page_size)))
        .scalars()
        .all()
    )
    return await _build_work_item_outs(db, list(items)), total


async def get_work_item_detail(db: AsyncSession, actor: Actor, work_item_id: str) -> WorkItemOut:
    item = await get_work_item(db, work_item_id, actor.tenant_id)
    return (await _build_work_item_outs(db, [item]))[0]


async def create_work_item_in_tx(
    db: AsyncSession,
    actor: Actor,
    project_id: str,
    data: WorkItemCreateIn,
    *,
    source: WorkItemSource = WorkItemSource.MANUAL,
    source_ref_id: str | None = None,
    reporter_id: str | None = None,
) -> WorkItem:
    """Create a work item (flush + activity + audit) WITHOUT committing, so callers that
    must combine it with their own writes in a single transaction can do so — e.g. intake
    accept-and-convert (`intake.service.accept_intake_request`). `create_work_item` is the
    committing public wrapper."""
    project = await ensure_project_writable(db, project_id, actor.tenant_id)
    custom_fields = validate_custom_fields(data.type, data.custom_fields)
    if data.assignee_id is not None:
        await _ensure_assignable(db, actor.tenant_id, project_id, data.assignee_id)
    seq = await _next_seq(db, project_id)
    item = WorkItem(
        tenant_id=actor.tenant_id,
        project_id=project_id,
        seq=seq,
        key=f"{project.key}-{seq}",
        type=data.type,
        title=data.title,
        description=data.description,
        status=WorkItemStatus.BACKLOG,
        priority=data.priority,
        assignee_id=data.assignee_id,
        reporter_id=reporter_id or actor.id,
        due_at=data.due_at,
        tags=list(data.tags),
        source=source,
        source_ref_id=source_ref_id,
        acceptance_criteria=data.acceptance_criteria,
        custom_fields=custom_fields,
        created_by=actor.id,
        updated_by=actor.id,
    )
    db.add(item)
    await db.flush()
    await _record_activity(db, actor, item.id, ActivityAction.CREATED, after={"type": item.type, "title": item.title})
    await audit.record(
        db,
        actor,
        action=AuditAction.WORK_ITEM_CREATE,
        resource_type="work_item",
        resource_id=item.id,
        project_id=project_id,
        after={"key": item.key, "type": item.type, "title": item.title, "source": item.source},
    )
    return item


async def create_work_item(
    db: AsyncSession,
    actor: Actor,
    project_id: str,
    data: WorkItemCreateIn,
    *,
    source: WorkItemSource = WorkItemSource.MANUAL,
    source_ref_id: str | None = None,
    reporter_id: str | None = None,
) -> WorkItemOut:
    item = await create_work_item_in_tx(
        db, actor, project_id, data, source=source, source_ref_id=source_ref_id, reporter_id=reporter_id
    )
    await db.commit()
    return (await _build_work_item_outs(db, [item]))[0]


async def update_work_item(db: AsyncSession, actor: Actor, work_item_id: str, data: WorkItemUpdateIn) -> WorkItemOut:
    item = await get_work_item(db, work_item_id, actor.tenant_id)
    await ensure_project_writable(db, item.project_id, actor.tenant_id)
    fields = data.model_fields_set
    before: dict[str, Any] = {}
    after: dict[str, Any] = {}
    activities: list[tuple[ActivityAction, str, Any, Any]] = []

    if "title" in fields and data.title is not None and data.title != item.title:
        before["title"], after["title"] = item.title, data.title
        activities.append((ActivityAction.TITLE_CHANGED, "title", item.title, data.title))
        item.title = data.title
    if "description" in fields and data.description != item.description:
        before["description"], after["description"] = item.description, data.description
        activities.append((ActivityAction.DESCRIPTION_CHANGED, "description", item.description, data.description))
        item.description = data.description
    if "priority" in fields and data.priority is not None and data.priority != item.priority:
        before["priority"], after["priority"] = item.priority, str(data.priority)
        activities.append((ActivityAction.PRIORITY_CHANGED, "priority", item.priority, str(data.priority)))
        item.priority = data.priority
    if "assignee_id" in fields and data.assignee_id != item.assignee_id:
        if data.assignee_id is not None:
            await _ensure_assignable(db, actor.tenant_id, item.project_id, data.assignee_id)
        before["assignee_id"], after["assignee_id"] = item.assignee_id, data.assignee_id
        activities.append((ActivityAction.ASSIGNEE_CHANGED, "assignee_id", item.assignee_id, data.assignee_id))
        item.assignee_id = data.assignee_id
    if "due_at" in fields and data.due_at != item.due_at:
        before["due_at"] = item.due_at.isoformat() if item.due_at else None
        after["due_at"] = data.due_at.isoformat() if data.due_at else None
        item.due_at = data.due_at
    if "tags" in fields and data.tags is not None and list(data.tags) != list(item.tags or []):
        before["tags"], after["tags"] = list(item.tags or []), list(data.tags)
        item.tags = list(data.tags)
    if "ai_summary" in fields and data.ai_summary != item.ai_summary:
        before["ai_summary"], after["ai_summary"] = item.ai_summary, data.ai_summary
        item.ai_summary = data.ai_summary
    if "acceptance_criteria" in fields and data.acceptance_criteria != item.acceptance_criteria:
        before["acceptance_criteria"], after["acceptance_criteria"] = (
            item.acceptance_criteria,
            data.acceptance_criteria,
        )
        item.acceptance_criteria = data.acceptance_criteria
    if "custom_fields" in fields and data.custom_fields is not None:
        validated = validate_custom_fields(WorkItemType(item.type), data.custom_fields)
        if validated != dict(item.custom_fields or {}):
            before["custom_fields"], after["custom_fields"] = dict(item.custom_fields or {}), validated
            item.custom_fields = validated

    if not after:
        return (await _build_work_item_outs(db, [item]))[0]

    item.updated_by = actor.id
    await db.flush()
    for action, field, prev, curr in activities:
        await _record_activity(db, actor, item.id, action, field=field, before={field: prev}, after={field: curr})
    await audit.record(
        db,
        actor,
        action=AuditAction.WORK_ITEM_UPDATE,
        resource_type="work_item",
        resource_id=item.id,
        project_id=item.project_id,
        before=before,
        after=after,
    )
    await db.commit()
    return (await _build_work_item_outs(db, [item]))[0]


async def transition_work_item(
    db: AsyncSession, actor: Actor, work_item_id: str, data: WorkItemTransitionIn
) -> WorkItemOut:
    item = await get_work_item(db, work_item_id, actor.tenant_id)
    await ensure_project_writable(db, item.project_id, actor.tenant_id)
    current = WorkItemStatus(item.status)
    target = data.status
    if target not in ALLOWED_TRANSITIONS[current]:
        raise BizError(ErrorCode.INVALID_STATUS_TRANSITION, f"cannot transition from {current} to {target}")
    item.status = target
    item.updated_by = actor.id
    await db.flush()
    await _record_activity(
        db,
        actor,
        item.id,
        ActivityAction.STATUS_CHANGED,
        field="status",
        before={"status": str(current)},
        after={"status": str(target)},
    )
    await audit.record(
        db,
        actor,
        action=AuditAction.WORK_ITEM_TRANSITION,
        resource_type="work_item",
        resource_id=item.id,
        project_id=item.project_id,
        before={"status": str(current)},
        after={"status": str(target)},
    )
    await db.commit()
    return (await _build_work_item_outs(db, [item]))[0]


async def delete_work_item(db: AsyncSession, actor: Actor, work_item_id: str) -> None:
    item = await get_work_item(db, work_item_id, actor.tenant_id)
    await ensure_project_writable(db, item.project_id, actor.tenant_id)
    item.deleted_at = _now()
    item.updated_by = actor.id
    await db.flush()
    await _record_activity(db, actor, item.id, ActivityAction.DELETED, after={"key": item.key})
    await audit.record(
        db,
        actor,
        action=AuditAction.WORK_ITEM_DELETE,
        resource_type="work_item",
        resource_id=item.id,
        project_id=item.project_id,
        before={"key": item.key, "title": item.title},
    )
    await db.commit()


# --- comments ---


async def _users_by_ids(db: AsyncSession, ids: set[str]) -> dict[str, User]:
    if not ids:
        return {}
    rows = (await db.execute(select(User).where(User.id.in_(ids)))).scalars().all()
    return {u.id: u for u in rows}


def _comment_out(comment: WorkItemComment, author: User | None) -> CommentOut:
    return CommentOut(
        id=comment.id,
        work_item_id=comment.work_item_id,
        author_type=CommentAuthorType(comment.author_type),
        author_id=comment.author_id,
        author=UserBriefOut.model_validate(author) if author is not None else None,
        body=comment.body,
        created_at=comment.created_at,
    )


async def list_comments(db: AsyncSession, actor: Actor, work_item_id: str) -> list[CommentOut]:
    await get_work_item(db, work_item_id, actor.tenant_id)
    rows = (
        (
            await db.execute(
                select(WorkItemComment)
                .where(WorkItemComment.work_item_id == work_item_id)
                .order_by(WorkItemComment.created_at)
            )
        )
        .scalars()
        .all()
    )
    users = await _users_by_ids(
        db, {c.author_id for c in rows if c.author_id and c.author_type == CommentAuthorType.USER}
    )
    return [_comment_out(c, users.get(c.author_id) if c.author_id else None) for c in rows]


async def create_comment(db: AsyncSession, actor: Actor, work_item_id: str, data: CommentCreateIn) -> CommentOut:
    item = await get_work_item(db, work_item_id, actor.tenant_id)
    await ensure_project_writable(db, item.project_id, actor.tenant_id)
    comment = WorkItemComment(
        tenant_id=actor.tenant_id,
        work_item_id=work_item_id,
        author_type=actor.type,
        author_id=actor.id,
        body=data.body,
    )
    db.add(comment)
    await db.flush()
    await _record_activity(db, actor, work_item_id, ActivityAction.COMMENTED, after={"comment_id": comment.id})
    await audit.record(
        db,
        actor,
        action=AuditAction.WORK_ITEM_COMMENT,
        resource_type="work_item",
        resource_id=work_item_id,
        project_id=item.project_id,
        after={"comment_id": comment.id},
    )
    await db.commit()
    author = await db.get(User, actor.id) if actor.type == ActorType.USER else None
    return _comment_out(comment, author)


# --- activities ---


def _activity_out(activity: WorkItemActivity, actor_user: User | None) -> ActivityOut:
    return ActivityOut(
        id=activity.id,
        work_item_id=activity.work_item_id,
        actor_type=activity.actor_type,
        actor_id=activity.actor_id,
        actor=UserBriefOut.model_validate(actor_user) if actor_user is not None else None,
        action=ActivityAction(activity.action),
        field=activity.field,
        before=activity.before,
        after=activity.after,
        created_at=activity.created_at,
    )


async def list_activities(db: AsyncSession, actor: Actor, work_item_id: str) -> list[ActivityOut]:
    await get_work_item(db, work_item_id, actor.tenant_id)
    rows = (
        (
            await db.execute(
                select(WorkItemActivity)
                .where(WorkItemActivity.work_item_id == work_item_id)
                .order_by(WorkItemActivity.created_at)
            )
        )
        .scalars()
        .all()
    )
    users = await _users_by_ids(db, {a.actor_id for a in rows if a.actor_id and a.actor_type == ActorType.USER})
    return [_activity_out(a, users.get(a.actor_id) if a.actor_id else None) for a in rows]


# --- relations ---


def _brief(item: WorkItem) -> WorkItemBriefOut:
    return WorkItemBriefOut(
        id=item.id,
        key=item.key,
        title=item.title,
        type=WorkItemType(item.type),
        status=WorkItemStatus(item.status),
    )


async def _work_items_by_ids(db: AsyncSession, ids: set[str]) -> dict[str, WorkItem]:
    if not ids:
        return {}
    rows = (await db.execute(select(WorkItem).where(WorkItem.id.in_(ids)))).scalars().all()
    return {w.id: w for w in rows}


async def list_relations(db: AsyncSession, actor: Actor, work_item_id: str) -> list[RelationOut]:
    await get_work_item(db, work_item_id, actor.tenant_id)
    rows = (
        (
            await db.execute(
                select(WorkItemRelation)
                .where(
                    (WorkItemRelation.source_work_item_id == work_item_id)
                    | (WorkItemRelation.target_work_item_id == work_item_id)
                )
                .order_by(WorkItemRelation.created_at)
            )
        )
        .scalars()
        .all()
    )
    other_ids = {
        r.target_work_item_id if r.source_work_item_id == work_item_id else r.source_work_item_id for r in rows
    }
    others = await _work_items_by_ids(db, other_ids)
    out: list[RelationOut] = []
    for r in rows:
        if r.source_work_item_id == work_item_id:
            direction = RelationDirection.OUTGOING
            other = others.get(r.target_work_item_id)
        else:
            direction = RelationDirection.INCOMING
            other = others.get(r.source_work_item_id)
        # Skip relations whose other end was soft-deleted.
        if other is None or other.deleted_at is not None:
            continue
        out.append(
            RelationOut(
                id=r.id, type=RelationType(r.type), direction=direction, related=_brief(other), created_at=r.created_at
            )
        )
    return out


async def create_relation(db: AsyncSession, actor: Actor, work_item_id: str, data: RelationCreateIn) -> RelationOut:
    source = await get_work_item(db, work_item_id, actor.tenant_id)
    await ensure_project_writable(db, source.project_id, actor.tenant_id)
    if data.type not in MANUAL_RELATION_TYPES:
        raise BizError(ErrorCode.INVALID_RELATION, "this relation type cannot be created manually")
    if data.target_work_item_id == work_item_id:
        raise BizError(ErrorCode.INVALID_RELATION, "cannot relate a work item to itself")
    target = await get_work_item(db, data.target_work_item_id, actor.tenant_id)
    if target.project_id != source.project_id:
        raise BizError(ErrorCode.INVALID_RELATION, "related work items must be in the same project")
    existing = (
        await db.execute(
            select(WorkItemRelation.id).where(
                WorkItemRelation.source_work_item_id == work_item_id,
                WorkItemRelation.target_work_item_id == data.target_work_item_id,
                WorkItemRelation.type == data.type,
            )
        )
    ).first()
    if existing is not None:
        raise BizError(ErrorCode.RELATION_ALREADY_EXISTS, "this relation already exists")
    relation = WorkItemRelation(
        tenant_id=actor.tenant_id,
        source_work_item_id=work_item_id,
        target_work_item_id=data.target_work_item_id,
        type=data.type,
        created_by=actor.id,
    )
    db.add(relation)
    await db.flush()
    detail = {"type": str(data.type), "target": data.target_work_item_id}
    await _record_activity(db, actor, work_item_id, ActivityAction.RELATION_ADDED, field="relation", after=detail)
    await audit.record(
        db,
        actor,
        action=AuditAction.WORK_ITEM_RELATION_ADD,
        resource_type="work_item",
        resource_id=work_item_id,
        project_id=source.project_id,
        after=detail,
    )
    await db.commit()
    return RelationOut(
        id=relation.id,
        type=RelationType(relation.type),
        direction=RelationDirection.OUTGOING,
        related=_brief(target),
        created_at=relation.created_at,
    )


async def delete_relation(db: AsyncSession, actor: Actor, work_item_id: str, relation_id: str) -> None:
    source = await get_work_item(db, work_item_id, actor.tenant_id)
    relation = await db.get(WorkItemRelation, relation_id)
    if (
        relation is None
        or relation.tenant_id != actor.tenant_id
        or work_item_id not in (relation.source_work_item_id, relation.target_work_item_id)
    ):
        raise BizError(ErrorCode.RELATION_NOT_FOUND, "relation not found")
    await ensure_project_writable(db, source.project_id, actor.tenant_id)
    detail = {
        "type": relation.type,
        "source": relation.source_work_item_id,
        "target": relation.target_work_item_id,
    }
    await db.delete(relation)
    await db.flush()
    await _record_activity(db, actor, work_item_id, ActivityAction.RELATION_REMOVED, field="relation", before=detail)
    await audit.record(
        db,
        actor,
        action=AuditAction.WORK_ITEM_RELATION_REMOVE,
        resource_type="work_item",
        resource_id=work_item_id,
        project_id=source.project_id,
        before=detail,
    )
    await db.commit()


# --- project summary + M7 dashboard metrics --------------------------------------
#
# `get_project_work_item_metrics` is the single source of truth for the project's
# work-item aggregates (status/type/priority/source distributions, high-priority /
# overdue / ai-created counts, 7-day created/completed trends). Both the M3 project
# overview (`get_project_summary`) and the M7 dashboard read it so their numbers can
# never drift (docs/modules/dashboard.md decision B).

_OPEN_STATUSES = [s for s in WorkItemStatus if s not in (WorkItemStatus.DONE, WorkItemStatus.CANCELLED)]
_HIGH_PRIORITIES = [WorkItemPriority.HIGH, WorkItemPriority.URGENT]
_AI_SOURCES = [WorkItemSource.AI_CHAT, WorkItemSource.MCP]
_PRIORITY_RANK = case(
    (WorkItem.priority == WorkItemPriority.URGENT, 0),
    (WorkItem.priority == WorkItemPriority.HIGH, 1),
    (WorkItem.priority == WorkItemPriority.MEDIUM, 2),
    (WorkItem.priority == WorkItemPriority.LOW, 3),
    else_=99,
)
# UTC date of a timestamptz column, timezone-stable regardless of the session TimeZone.
_UTC_DAY = func.date(func.timezone("UTC", WorkItem.created_at))
_ACTIVITY_UTC_DAY = func.date(func.timezone("UTC", WorkItemActivity.created_at))


def _grouped(rows: Sequence[Any], enum_cls: type[StrEnum]) -> dict[str, int]:
    counts = {str(v): 0 for v in enum_cls}
    for value, count in rows:
        counts[str(value)] = count
    return counts


def _build_trend(today: date, rows: Sequence[Any]) -> list[DailyCount]:
    """Zero-fill the last 7 UTC days (oldest first) from (date, count) rows."""
    by_day = {(d.isoformat() if hasattr(d, "isoformat") else str(d)): int(c) for d, c in rows}
    days = [(today - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
    return [DailyCount(date=day, count=by_day.get(day, 0)) for day in days]


async def get_project_work_item_metrics(db: AsyncSession, actor: Actor, project_id: str) -> WorkItemMetrics:
    await projects_service.get_project(db, project_id, actor.tenant_id)
    now = _now()
    window_start = datetime.combine(now.date() - timedelta(days=6), time.min, tzinfo=UTC)
    conds = (
        WorkItem.tenant_id == actor.tenant_id,
        WorkItem.project_id == project_id,
        WorkItem.deleted_at.is_(None),
    )

    async def _count(*extra: Any) -> int:
        return (await db.execute(select(func.count()).select_from(WorkItem).where(*conds, *extra))).scalar_one()

    async def _dist(column: Any, enum_cls: type[StrEnum]) -> dict[str, int]:
        rows = (await db.execute(select(column, func.count()).where(*conds).group_by(column))).all()
        return _grouped(rows, enum_cls)

    status_counts = await _dist(WorkItem.status, WorkItemStatus)
    type_counts = await _dist(WorkItem.type, WorkItemType)
    priority_counts = await _dist(WorkItem.priority, WorkItemPriority)
    source_counts = await _dist(WorkItem.source, WorkItemSource)
    high_priority_count = await _count(WorkItem.priority.in_(_HIGH_PRIORITIES))
    overdue_count = await _count(
        WorkItem.due_at.is_not(None), WorkItem.due_at < now, WorkItem.status.in_(_OPEN_STATUSES)
    )
    ai_created_count = await _count(WorkItem.source.in_(_AI_SOURCES))

    created_rows = (
        await db.execute(
            select(_UTC_DAY, func.count()).where(*conds, WorkItem.created_at >= window_start).group_by(_UTC_DAY)
        )
    ).all()
    completed_rows = (
        await db.execute(
            select(_ACTIVITY_UTC_DAY, func.count())
            .select_from(WorkItemActivity)
            .join(WorkItem, WorkItem.id == WorkItemActivity.work_item_id)
            .where(
                *conds,
                WorkItemActivity.action == ActivityAction.STATUS_CHANGED,
                WorkItemActivity.after["status"].astext == WorkItemStatus.DONE,
                WorkItemActivity.created_at >= window_start,
            )
            .group_by(_ACTIVITY_UTC_DAY)
        )
    ).all()

    return WorkItemMetrics(
        total_count=sum(status_counts.values()),
        status_counts=status_counts,
        type_counts=type_counts,
        priority_counts=priority_counts,
        source_counts=source_counts,
        high_priority_count=high_priority_count,
        overdue_count=overdue_count,
        ai_created_count=ai_created_count,
        created_trend=_build_trend(now.date(), created_rows),
        completed_trend=_build_trend(now.date(), completed_rows),
    )


async def list_project_overdue_work_items(
    db: AsyncSession, actor: Actor, project_id: str, params: PageParams
) -> tuple[list[OverdueWorkItem], int]:
    await projects_service.get_project(db, project_id, actor.tenant_id)
    now = _now()
    base = select(WorkItem).where(
        WorkItem.tenant_id == actor.tenant_id,
        WorkItem.project_id == project_id,
        WorkItem.deleted_at.is_(None),
        WorkItem.due_at.is_not(None),
        WorkItem.due_at < now,
        WorkItem.status.in_(_OPEN_STATUSES),
    )
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    items = (
        (
            await db.execute(
                base.order_by(WorkItem.due_at.asc(), _PRIORITY_RANK.asc(), WorkItem.created_at.desc())
                .offset(params.offset)
                .limit(params.page_size)
            )
        )
        .scalars()
        .all()
    )
    users = await _users_by_ids(db, {i.assignee_id for i in items if i.assignee_id})
    rows: list[OverdueWorkItem] = []
    for i in items:
        if i.due_at is None:  # guaranteed by the query; narrows the optional for the type checker
            continue
        due = _aware(i.due_at)
        rows.append(
            OverdueWorkItem(
                id=i.id,
                key=i.key,
                title=i.title,
                status=WorkItemStatus(i.status),
                type=WorkItemType(i.type),
                priority=WorkItemPriority(i.priority),
                assignee_id=i.assignee_id,
                assignee=UserBriefOut.model_validate(users[i.assignee_id]) if i.assignee_id in users else None,
                due_at=due,
                days_overdue=max(0, (now - due).days),
                source=WorkItemSource(i.source),
                created_at=i.created_at,
            )
        )
    return rows, total


async def get_project_workload_metrics(db: AsyncSession, actor: Actor, project_id: str) -> list[WorkloadBucket]:
    await projects_service.get_project(db, project_id, actor.tenant_id)
    now = _now()
    conds = (
        WorkItem.tenant_id == actor.tenant_id,
        WorkItem.project_id == project_id,
        WorkItem.deleted_at.is_(None),
    )
    status_rows = (
        await db.execute(
            select(WorkItem.assignee_id, WorkItem.status, func.count())
            .where(*conds)
            .group_by(WorkItem.assignee_id, WorkItem.status)
        )
    ).all()
    overdue_rows = (
        await db.execute(
            select(WorkItem.assignee_id, func.count())
            .where(*conds, WorkItem.due_at.is_not(None), WorkItem.due_at < now, WorkItem.status.in_(_OPEN_STATUSES))
            .group_by(WorkItem.assignee_id)
        )
    ).all()
    high_rows = (
        await db.execute(
            select(WorkItem.assignee_id, func.count())
            .where(*conds, WorkItem.priority.in_(_HIGH_PRIORITIES))
            .group_by(WorkItem.assignee_id)
        )
    ).all()

    buckets: dict[str | None, dict[str, int]] = {}
    totals: dict[str | None, int] = {}
    for assignee_id, status, count in status_rows:
        buckets.setdefault(assignee_id, {})[str(status)] = count
        totals[assignee_id] = totals.get(assignee_id, 0) + count
    overdue_by: dict[str | None, int] = {row[0]: row[1] for row in overdue_rows}
    high_by: dict[str | None, int] = {row[0]: row[1] for row in high_rows}

    users = await _users_by_ids(db, {a for a in buckets if a})
    result = [
        WorkloadBucket(
            assignee_id=assignee_id,
            assignee=UserBriefOut.model_validate(users[assignee_id]) if assignee_id in users else None,
            total_count=totals.get(assignee_id, 0),
            status_counts=status_counts,
            overdue_count=overdue_by.get(assignee_id, 0),
            high_priority_count=high_by.get(assignee_id, 0),
        )
        for assignee_id, status_counts in buckets.items()
    ]
    result.sort(key=lambda b: b.total_count, reverse=True)
    return result


async def get_project_summary(db: AsyncSession, actor: Actor, project_id: str) -> ProjectSummaryOut:
    metrics = await get_project_work_item_metrics(db, actor, project_id)
    recent_rows = (
        await db.execute(
            select(WorkItemActivity, WorkItem.key, WorkItem.title)
            .join(WorkItem, WorkItem.id == WorkItemActivity.work_item_id)
            .where(
                WorkItem.tenant_id == actor.tenant_id,
                WorkItem.project_id == project_id,
                WorkItem.deleted_at.is_(None),
            )
            .order_by(WorkItemActivity.created_at.desc())
            .limit(5)
        )
    ).all()
    recent = [
        ProjectActivityOut(
            id=activity.id,
            work_item_id=activity.work_item_id,
            work_item_key=key,
            work_item_title=title,
            action=ActivityAction(activity.action),
            actor_type=activity.actor_type,
            actor_id=activity.actor_id,
            created_at=activity.created_at,
        )
        for activity, key, title in recent_rows
    ]
    return ProjectSummaryOut(
        total_count=metrics.total_count,
        status_counts=metrics.status_counts,
        high_priority_count=metrics.high_priority_count,
        overdue_count=metrics.overdue_count,
        ai_created_count=metrics.ai_created_count,
        recent_activities=recent,
    )
