from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.access import TENANT_ROLES, Permission, Scope, ScopeType, Subject, can, get_current_subject
from worknexus.core.errors import BizError, ErrorCode
from worknexus.db import get_db
from worknexus.modules.workchat.models import AgentAction, Conversation


def accessible_project_ids(subject: Subject) -> set[str] | None:
    """Projects whose agent actions this subject may list. None = tenant-wide (owner/admin);
    otherwise the subject's project memberships only."""
    if any(role in TENANT_ROLES for role in subject.tenant_roles):
        return None
    return set(subject.project_roles.keys())


def require_conversation_permission(action: Permission) -> Callable[..., Coroutine[Any, Any, Subject]]:
    """Resolve the conversation's project, then run the project-scoped permission check."""

    async def dependency(
        conversation_id: str,
        db: Annotated[AsyncSession, Depends(get_db)],
        subject: Annotated[Subject, Depends(get_current_subject)],
    ) -> Subject:
        conversation = await db.get(Conversation, conversation_id)
        if (
            conversation is None
            or conversation.tenant_id != subject.actor.tenant_id
            or conversation.deleted_at is not None
        ):
            raise BizError(ErrorCode.CONVERSATION_NOT_FOUND, "conversation not found")
        scope = Scope(type=ScopeType.PROJECT, project_id=conversation.project_id)
        if not can(subject, action, scope):
            raise BizError(ErrorCode.FORBIDDEN, "permission denied")
        return subject

    return dependency


def require_agent_action_permission(action: Permission) -> Callable[..., Coroutine[Any, Any, Subject]]:
    """Resolve the agent action's project, then run the project-scoped permission check."""

    async def dependency(
        agent_action_id: str,
        db: Annotated[AsyncSession, Depends(get_db)],
        subject: Annotated[Subject, Depends(get_current_subject)],
    ) -> Subject:
        agent_action = await db.get(AgentAction, agent_action_id)
        if agent_action is None or agent_action.tenant_id != subject.actor.tenant_id:
            raise BizError(ErrorCode.AGENT_ACTION_NOT_FOUND, "agent action not found")
        scope = Scope(type=ScopeType.PROJECT, project_id=agent_action.project_id)
        if not can(subject, action, scope):
            raise BizError(ErrorCode.FORBIDDEN, "permission denied")
        return subject

    return dependency
