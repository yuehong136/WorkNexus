"""workchat service: conversations, messages, and the AgentAction confirmation chain.

Single write entry for the workchat domain (REST routers and the skills middleware
both call in here). The AgentAction lifecycle:

  propose  — the /mcp middleware turns a permitted low_write tool call into
             `create_pending_agent_action` (status=pending) instead of executing it.
  approve  — `approve_and_execute` re-runs the live double-check (user ∧ agent ∧
             resource ∧ risk ∧ confirmation), then dispatches tool_name → the matching
             work_items.service write, executed as the AI-agent actor.
  reject   — `reject` records the user's decision.

`permissions_snapshot` stored at propose time is evidence only; it never substitutes
for the live permission check at approval.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.config import get_settings
from worknexus.core.access import Permission, Scope, ScopeType, can, load_subject
from worknexus.core.deps import Actor, ActorType
from worknexus.core.errors import BizError, ErrorCode
from worknexus.core.pagination import PageParams
from worknexus.modules.audit import service as audit
from worknexus.modules.audit.service import AuditAction
from worknexus.modules.identity.schemas import DelegationContext
from worknexus.modules.projects import service as projects_service
from worknexus.modules.work_items import service as work_items_service
from worknexus.modules.work_items.schemas import (
    CommentCreateIn,
    WorkItemCreateIn,
    WorkItemPriority,
    WorkItemSource,
    WorkItemStatus,
    WorkItemTransitionIn,
    WorkItemType,
    WorkItemUpdateIn,
)
from worknexus.modules.workchat.models import AgentAction, Conversation, Message
from worknexus.modules.workchat.schemas import (
    AgentActionOut,
    AgentActionStatus,
    AgentActionType,
    ConversationOut,
    MessageCreateIn,
    MessageOut,
    MessageRole,
    RiskLevel,
)

# tool_name (namespace-prefixed) → confirmable action + the underlying permission the
# user and agent must both hold at approval time. Shared by the propose and execute paths.
_TOOL_TO_ACTION: dict[str, AgentActionType] = {
    "workitem_create_work_item": AgentActionType.CREATE_WORK_ITEM,
    "workitem_update_work_item": AgentActionType.UPDATE_WORK_ITEM,
    "workitem_transition_work_item": AgentActionType.TRANSITION_WORK_ITEM,
    "workitem_comment_work_item": AgentActionType.COMMENT_WORK_ITEM,
}

_ACTION_PERMISSION: dict[AgentActionType, Permission] = {
    AgentActionType.CREATE_WORK_ITEM: Permission.WORK_ITEM_CREATE,
    AgentActionType.UPDATE_WORK_ITEM: Permission.WORK_ITEM_UPDATE,
    AgentActionType.TRANSITION_WORK_ITEM: Permission.WORK_ITEM_TRANSITION,
    AgentActionType.COMMENT_WORK_ITEM: Permission.WORK_ITEM_COMMENT,
}


def _now() -> datetime:
    return datetime.now(UTC)


# --- conversations ---------------------------------------------------------------


async def get_or_create_default_conversation(db: AsyncSession, actor: Actor, project_id: str) -> Conversation:
    await projects_service.get_project(db, project_id, actor.tenant_id)
    existing = (
        await db.execute(
            select(Conversation)
            .where(
                Conversation.tenant_id == actor.tenant_id,
                Conversation.project_id == project_id,
                Conversation.kind == "default",
                Conversation.deleted_at.is_(None),
            )
            .order_by(Conversation.created_at)
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    conversation = Conversation(
        tenant_id=actor.tenant_id,
        project_id=project_id,
        kind="default",
        created_by=actor.id,
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def list_conversations(db: AsyncSession, actor: Actor, project_id: str) -> list[ConversationOut]:
    # v0.1 keeps a single default conversation per project; create it on first read.
    conversation = await get_or_create_default_conversation(db, actor, project_id)
    return [ConversationOut.model_validate(conversation)]


async def get_conversation(db: AsyncSession, actor: Actor, conversation_id: str) -> Conversation:
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None or conversation.tenant_id != actor.tenant_id or conversation.deleted_at is not None:
        raise BizError(ErrorCode.CONVERSATION_NOT_FOUND, "conversation not found")
    return conversation


# --- messages --------------------------------------------------------------------


async def list_messages(
    db: AsyncSession, actor: Actor, conversation_id: str, *, params: PageParams
) -> tuple[list[MessageOut], int]:
    await get_conversation(db, actor, conversation_id)
    base = select(Message).where(Message.conversation_id == conversation_id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (
        (await db.execute(base.order_by(Message.created_at.desc()).offset(params.offset).limit(params.page_size)))
        .scalars()
        .all()
    )
    # Newest-first page, returned oldest-first for natural chat rendering.
    return [MessageOut.model_validate(m) for m in reversed(rows)], total


async def create_user_message(
    db: AsyncSession, actor: Actor, conversation_id: str, data: MessageCreateIn
) -> MessageOut:
    await get_conversation(db, actor, conversation_id)
    message = Message(
        tenant_id=actor.tenant_id,
        conversation_id=conversation_id,
        role=MessageRole.USER,
        content=data.content,
        created_by=actor.id,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return MessageOut.model_validate(message)


async def create_ai_message(
    db: AsyncSession,
    actor: Actor,
    conversation_id: str,
    *,
    content: str,
    run_id: str,
    agent_action_id: str | None = None,
    work_item_id: str | None = None,
    knowledge_refs: list[dict[str, Any]] | None = None,
) -> Message:
    """Persist the AI turn at the end of a run. `created_by` is null (authored by the agent)."""
    message = Message(
        tenant_id=actor.tenant_id,
        conversation_id=conversation_id,
        role=MessageRole.AI,
        content=content,
        run_id=run_id,
        agent_action_id=agent_action_id,
        work_item_id=work_item_id,
        knowledge_refs=knowledge_refs,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


async def get_run(db: AsyncSession, actor: Actor, run_id: str) -> list[MessageOut]:
    """Compensation read after a dropped SSE connection: the messages of one run, scoped
    to a conversation the caller can access."""
    rows = (
        (
            await db.execute(
                select(Message)
                .where(Message.tenant_id == actor.tenant_id, Message.run_id == run_id)
                .order_by(Message.created_at)
            )
        )
        .scalars()
        .all()
    )
    if not rows:
        raise BizError(ErrorCode.WORKCHAT_RUN_NOT_FOUND, "run not found")
    conversation = await get_conversation(db, actor, rows[0].conversation_id)
    subject = await load_subject(db, actor)
    if not can(subject, Permission.WORKCHAT_USE, Scope(type=ScopeType.PROJECT, project_id=conversation.project_id)):
        raise BizError(ErrorCode.FORBIDDEN, "permission denied")
    return [MessageOut.model_validate(m) for m in rows]


# --- agent actions: propose ------------------------------------------------------


async def create_pending_agent_action(
    db: AsyncSession,
    delegation: DelegationContext,
    *,
    tool_name: str,
    arguments: dict[str, Any],
    skill_invocation_id: str,
) -> AgentAction:
    """Called by the skills middleware on a permitted low_write tool call. Writes the
    pending row + audit on the caller's session; the middleware owns the commit."""
    action_type = _TOOL_TO_ACTION.get(tool_name)
    if action_type is None:
        raise BizError(ErrorCode.INVALID_INPUT, f"tool {tool_name} cannot be proposed as an agent action")
    if delegation.project_id is None:
        raise BizError(ErrorCode.INVALID_INPUT, "delegation token is not bound to a project")
    ttl = get_settings().agent_action_pending_ttl_seconds
    action = AgentAction(
        tenant_id=delegation.tenant_id,
        conversation_id=delegation.conversation_id,
        project_id=delegation.project_id,
        action_type=action_type,
        arguments=dict(arguments or {}),
        risk_level=RiskLevel.LOW_WRITE,
        status=AgentActionStatus.PENDING,
        requested_by_user_id=delegation.user_id,
        agent_id=delegation.agent_id,
        permissions_snapshot=delegation.permissions_snapshot,
        skill_invocation_id=skill_invocation_id,
        expires_at=_now() + timedelta(seconds=ttl),
        created_by=delegation.agent_id,
        updated_by=delegation.agent_id,
    )
    db.add(action)
    await db.flush()
    actor = Actor(id=delegation.agent_id, type=ActorType.AI_AGENT, tenant_id=delegation.tenant_id)
    await audit.record(
        db,
        actor,
        action=AuditAction.AI_PROPOSED_ACTION_CREATE,
        resource_type="agent_action",
        resource_id=action.id,
        project_id=delegation.project_id,
        detail={"actionType": action_type.value, "tool": tool_name, "skillInvocationId": skill_invocation_id},
    )
    await db.flush()
    return action


# --- agent actions: read ---------------------------------------------------------


async def _get_agent_action_row(db: AsyncSession, actor: Actor, agent_action_id: str) -> AgentAction:
    action = await db.get(AgentAction, agent_action_id)
    if action is None or action.tenant_id != actor.tenant_id:
        raise BizError(ErrorCode.AGENT_ACTION_NOT_FOUND, "agent action not found")
    return action


async def _maybe_expire(db: AsyncSession, action: AgentAction) -> None:
    if action.status == AgentActionStatus.PENDING and action.expires_at is not None and action.expires_at <= _now():
        action.status = AgentActionStatus.EXPIRED
        await db.commit()
        await db.refresh(action)


async def get_agent_action(db: AsyncSession, actor: Actor, agent_action_id: str) -> AgentActionOut:
    action = await _get_agent_action_row(db, actor, agent_action_id)
    await _maybe_expire(db, action)
    return AgentActionOut.model_validate(action)


async def list_agent_actions(
    db: AsyncSession,
    actor: Actor,
    *,
    accessible_project_ids: set[str] | None,
    params: PageParams,
    status: AgentActionStatus | None = None,
    project_id: str | None = None,
) -> tuple[list[AgentActionOut], int]:
    """`accessible_project_ids=None` means tenant-wide visibility (owner/admin); a set
    restricts to the caller's projects (D6: never surface actions the user can't see)."""
    base = select(AgentAction).where(AgentAction.tenant_id == actor.tenant_id)
    if accessible_project_ids is not None:
        if not accessible_project_ids:
            return [], 0
        base = base.where(AgentAction.project_id.in_(accessible_project_ids))
    if status is not None:
        base = base.where(AgentAction.status == status)
    if project_id is not None:
        base = base.where(AgentAction.project_id == project_id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (
        (await db.execute(base.order_by(AgentAction.created_at.desc()).offset(params.offset).limit(params.page_size)))
        .scalars()
        .all()
    )
    return [AgentActionOut.model_validate(r) for r in rows], total


# --- agent actions: approve / reject ---------------------------------------------


def _agent_actor(action: AgentAction) -> Actor:
    return Actor(id=action.agent_id, type=ActorType.AI_AGENT, tenant_id=action.tenant_id)


async def _check_live_permissions(db: AsyncSession, user: Actor, action: AgentAction) -> None:
    """D5 double-check at approval: user ∧ agent ∧ confirmation right, all live (the
    stored snapshot is evidence only). Resource ∧ risk are enforced downstream (the
    work_items service blocks archived projects / invalid states; risk is low_write)."""
    action_type = AgentActionType(action.action_type)
    permission = _ACTION_PERMISSION[action_type]
    scope = Scope(type=ScopeType.PROJECT, project_id=action.project_id)
    user_subject = await load_subject(db, user)
    if not can(user_subject, Permission.AGENT_ACTION_CONFIRM, scope):
        raise BizError(ErrorCode.FORBIDDEN, "permission denied")
    if not can(user_subject, permission, scope):
        raise BizError(ErrorCode.FORBIDDEN, "permission denied")
    agent_subject = await load_subject(db, _agent_actor(action))
    if not can(agent_subject, permission, scope):
        raise BizError(ErrorCode.FORBIDDEN, "agent is not permitted to perform this action")


async def _dispatch(db: AsyncSession, action: AgentAction) -> tuple[str, str]:
    """Map the proposed tool call to the matching work_items.service write, executed as
    the AI-agent actor. reporter_id must be the requesting user (created_by accepts the
    agent id, but reporter_id is a users FK)."""
    actor = _agent_actor(action)
    args = dict(action.arguments or {})
    action_type = AgentActionType(action.action_type)
    if action_type == AgentActionType.CREATE_WORK_ITEM:
        data = WorkItemCreateIn(
            type=WorkItemType(args.get("type", "task")),
            title=args["title"],
            description=args.get("description"),
            priority=WorkItemPriority(args.get("priority", "medium")),
            assignee_id=args.get("assignee_id"),
            tags=args.get("tags") or [],
            custom_fields=args.get("custom_fields") or {},
        )
        result = await work_items_service.create_work_item(
            db,
            actor,
            action.project_id,
            data,
            source=WorkItemSource.AI_CHAT,
            source_ref_id=action.id,
            reporter_id=action.requested_by_user_id,
        )
        return "work_item", result.id
    if action_type == AgentActionType.UPDATE_WORK_ITEM:
        work_item_id = args["work_item_id"]
        payload: dict[str, Any] = {}
        if args.get("title") is not None:
            payload["title"] = args["title"]
        if args.get("description") is not None:
            payload["description"] = args["description"]
        if args.get("priority") is not None:
            payload["priority"] = WorkItemPriority(args["priority"])
        if args.get("assignee_id") is not None:
            payload["assignee_id"] = args["assignee_id"]
        if args.get("custom_fields") is not None:
            payload["custom_fields"] = args["custom_fields"]
        result = await work_items_service.update_work_item(db, actor, work_item_id, WorkItemUpdateIn(**payload))
        return "work_item", result.id
    if action_type == AgentActionType.TRANSITION_WORK_ITEM:
        work_item_id = args["work_item_id"]
        result = await work_items_service.transition_work_item(
            db, actor, work_item_id, WorkItemTransitionIn(status=WorkItemStatus(args["status"]))
        )
        return "work_item", result.id
    # COMMENT_WORK_ITEM
    work_item_id = args["work_item_id"]
    await work_items_service.create_comment(db, actor, work_item_id, CommentCreateIn(body=args["body"]))
    return "work_item", work_item_id


async def approve_and_execute(db: AsyncSession, actor: Actor, agent_action_id: str) -> AgentActionOut:
    action = await _get_agent_action_row(db, actor, agent_action_id)
    await _maybe_expire(db, action)
    if action.status == AgentActionStatus.EXPIRED:
        raise BizError(ErrorCode.AGENT_ACTION_EXPIRED, "agent action has expired")
    if action.status != AgentActionStatus.PENDING:
        raise BizError(ErrorCode.AGENT_ACTION_NOT_PENDING, "agent action is not pending")

    await _check_live_permissions(db, actor, action)

    # Phase 1: record the approval durably before touching business data.
    now = _now()
    action.status = AgentActionStatus.APPROVED
    action.approved_by_user_id = actor.id
    action.approved_at = now
    action.updated_by = actor.id
    await audit.record(
        db,
        actor,
        action=AuditAction.AGENT_ACTION_APPROVE,
        resource_type="agent_action",
        resource_id=action.id,
        project_id=action.project_id,
        detail={"actionType": action.action_type},
    )
    await db.commit()

    # Phase 2 + 3: dispatch the real write (work_items.service commits it), then finalize.
    try:
        result_ref = await _dispatch(db, action)
    except (BizError, KeyError, ValueError, ValidationError) as exc:
        await db.rollback()
        action = await _get_agent_action_row(db, actor, agent_action_id)
        message = exc.message if isinstance(exc, BizError) else str(exc)
        action.status = AgentActionStatus.FAILED
        action.error_message = message
        action.executed_at = _now()
        action.updated_by = actor.id
        await audit.record(
            db,
            actor,
            action=AuditAction.AGENT_ACTION_EXECUTE,
            resource_type="agent_action",
            resource_id=action.id,
            project_id=action.project_id,
            detail={"ok": False, "error": message},
        )
        await db.commit()
        await db.refresh(action)
        return AgentActionOut.model_validate(action)

    action.status = AgentActionStatus.EXECUTED
    action.result_ref_type, action.result_ref_id = result_ref
    action.executed_at = _now()
    action.updated_by = actor.id
    await audit.record(
        db,
        actor,
        action=AuditAction.AGENT_ACTION_EXECUTE,
        resource_type="agent_action",
        resource_id=action.id,
        project_id=action.project_id,
        detail={"ok": True, "resultRefType": result_ref[0], "resultRefId": result_ref[1]},
    )
    await db.commit()
    await db.refresh(action)
    return AgentActionOut.model_validate(action)


async def reject(db: AsyncSession, actor: Actor, agent_action_id: str, reason: str | None = None) -> AgentActionOut:
    action = await _get_agent_action_row(db, actor, agent_action_id)
    await _maybe_expire(db, action)
    if action.status == AgentActionStatus.EXPIRED:
        raise BizError(ErrorCode.AGENT_ACTION_EXPIRED, "agent action has expired")
    if action.status != AgentActionStatus.PENDING:
        raise BizError(ErrorCode.AGENT_ACTION_NOT_PENDING, "agent action is not pending")
    action.status = AgentActionStatus.REJECTED
    action.approved_by_user_id = actor.id
    action.rejected_at = _now()
    action.rejection_reason = reason
    action.updated_by = actor.id
    await audit.record(
        db,
        actor,
        action=AuditAction.AGENT_ACTION_REJECT,
        resource_type="agent_action",
        resource_id=action.id,
        project_id=action.project_id,
        detail={"actionType": action.action_type, "reason": reason},
    )
    await db.commit()
    await db.refresh(action)
    return AgentActionOut.model_validate(action)
