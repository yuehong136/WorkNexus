from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.deps import Actor
from worknexus.core.pagination import PageParams
from worknexus.core.request_id import get_request_id
from worknexus.modules.audit.models import AuditLog
from worknexus.modules.audit.schemas import AuditActorOut, AuditActorType, AuditLogOut

# Direct leaf-model reads to resolve display names. `audit` is imported by every module's
# write path (record), so it must not import identity/projects *services* (would cycle);
# selecting their leaf models mirrors skills._load_users / work_items._users_by_ids.
from worknexus.modules.identity.models import AIAgent, User
from worknexus.modules.projects.models import Project


class AuditAction(StrEnum):
    SETUP_COMPLETE = "setup.complete"
    AUTH_LOGIN = "auth.login"
    AUTH_LOGOUT = "auth.logout"
    INVITE_CREATE = "invite.create"
    INVITE_REVOKE = "invite.revoke"
    INVITE_ACCEPT = "invite.accept"
    ROLE_BINDING_CREATE = "role_binding.create"
    ROLE_BINDING_DELETE = "role_binding.delete"
    PROJECT_CREATE = "project.create"
    PROJECT_UPDATE = "project.update"
    PROJECT_ARCHIVE = "project.archive"
    PROJECT_MEMBER_ADD = "project.member.add"
    PROJECT_MEMBER_UPDATE = "project.member.update"
    PROJECT_MEMBER_REMOVE = "project.member.remove"
    WORK_ITEM_CREATE = "work_item.create"
    WORK_ITEM_UPDATE = "work_item.update"
    WORK_ITEM_DELETE = "work_item.delete"
    WORK_ITEM_TRANSITION = "work_item.transition"
    WORK_ITEM_COMMENT = "work_item.comment"
    WORK_ITEM_RELATION_ADD = "work_item.relation.add"
    WORK_ITEM_RELATION_REMOVE = "work_item.relation.remove"
    SKILL_INVOKE = "skill.invoke"
    AI_PROPOSED_ACTION_CREATE = "ai.proposed_action.create"
    AGENT_ACTION_APPROVE = "agent_action.approve"
    AGENT_ACTION_REJECT = "agent_action.reject"
    AGENT_ACTION_EXECUTE = "agent_action.execute"
    INTAKE_CREATE = "intake.create"
    INTAKE_UPDATE = "intake.update"
    INTAKE_ACCEPT = "intake.accept"
    INTAKE_REJECT = "intake.reject"
    INTAKE_MARK_DUPLICATE = "intake.duplicate"
    INTAKE_SNOOZE = "intake.snooze"
    USER_PROFILE_UPDATE = "user.profile.update"


async def record(
    db: AsyncSession,
    actor: Actor,
    *,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    project_id: str | None = None,
    detail: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Add an audit row to the caller's session. Never commits — the audit row
    must live or die with the business write in the same transaction."""
    log = AuditLog(
        tenant_id=actor.tenant_id,
        actor_type=actor.type,
        actor_id=actor.id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        project_id=project_id,
        before=before,
        after=after,
        detail=detail,
        request_id=get_request_id(),
        ip_address=ip_address,
    )
    db.add(log)
    await db.flush()
    return log


async def _names_by_ids[M: (User, AIAgent, Project)](db: AsyncSession, model: type[M], ids: set[str]) -> dict[str, M]:
    if not ids:
        return {}
    rows = (await db.execute(select(model).where(model.id.in_(ids)))).scalars().all()
    return {row.id: row for row in rows}


def _to_out(
    row: AuditLog,
    users: dict[str, User],
    agents: dict[str, AIAgent],
    projects: dict[str, Project],
) -> AuditLogOut:
    actor_type = AuditActorType(row.actor_type)
    display_name: str | None = None
    if row.actor_id is not None:
        if actor_type == AuditActorType.USER and (user := users.get(row.actor_id)) is not None:
            display_name = user.display_name
        elif actor_type == AuditActorType.AI_AGENT and (agent := agents.get(row.actor_id)) is not None:
            display_name = agent.name
    project = projects.get(row.project_id) if row.project_id is not None else None
    return AuditLogOut(
        id=row.id,
        created_at=row.created_at,
        actor=AuditActorOut(type=actor_type, id=row.actor_id, display_name=display_name),
        action=row.action,
        resource_type=row.resource_type,
        resource_id=row.resource_id,
        project_id=row.project_id,
        project_name=project.name if project is not None else None,
        before=row.before,
        after=row.after,
        detail=row.detail,
        request_id=row.request_id,
        ip_address=row.ip_address,
    )


async def list_audit_logs(
    db: AsyncSession,
    actor: Actor,
    *,
    params: PageParams,
    actor_type: AuditActorType | None = None,
    actor_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    project_id: str | None = None,
    action: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> tuple[list[AuditLogOut], int]:
    """Tenant-scoped read of audit_logs. Pure read — no write, no audit-of-audit.

    Display names for the page's actors and projects are resolved in batch."""
    base = select(AuditLog).where(AuditLog.tenant_id == actor.tenant_id)
    if actor_type is not None:
        base = base.where(AuditLog.actor_type == actor_type)
    if actor_id is not None:
        base = base.where(AuditLog.actor_id == actor_id)
    if resource_type is not None:
        base = base.where(AuditLog.resource_type == resource_type)
    if resource_id is not None:
        base = base.where(AuditLog.resource_id == resource_id)
    if project_id is not None:
        base = base.where(AuditLog.project_id == project_id)
    if action is not None:
        base = base.where(AuditLog.action == action)
    if created_from is not None:
        base = base.where(AuditLog.created_at >= created_from)
    if created_to is not None:
        base = base.where(AuditLog.created_at <= created_to)

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = list(
        (await db.execute(base.order_by(AuditLog.created_at.desc()).offset(params.offset).limit(params.page_size)))
        .scalars()
        .all()
    )

    users = await _names_by_ids(
        db, User, {r.actor_id for r in rows if r.actor_type == AuditActorType.USER and r.actor_id}
    )
    agents = await _names_by_ids(
        db, AIAgent, {r.actor_id for r in rows if r.actor_type == AuditActorType.AI_AGENT and r.actor_id}
    )
    projects = await _names_by_ids(db, Project, {r.project_id for r in rows if r.project_id})
    return [_to_out(r, users, agents, projects) for r in rows], total
