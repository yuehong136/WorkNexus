from enum import StrEnum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.deps import Actor
from worknexus.core.request_id import get_request_id
from worknexus.modules.audit.models import AuditLog


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
