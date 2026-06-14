"""Workchat run orchestration: build a permission-filtered context (D6), issue a
delegation token, stream multirag, and re-emit a clean WorkNexus event schema.

This module orchestrates; all writes go through `workchat.service`. Proposed actions are
created server-side by the skills middleware when multirag calls back `/mcp`; here we only
surface the AgentAction a `tool_result` frame references — we never create one from the
stream (that would bypass the dual-token gate).
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.config import Settings
from worknexus.core.access import Permission, Scope, ScopeType, Subject, can
from worknexus.core.deps import Actor
from worknexus.core.errors import BizError, ErrorCode
from worknexus.core.pagination import PageParams
from worknexus.modules.identity import service as identity_service
from worknexus.modules.identity.models import AIAgent
from worknexus.modules.identity.schemas import AgentStatus, DelegationContext
from worknexus.modules.projects import service as projects_service
from worknexus.modules.work_items.models import WorkItem
from worknexus.modules.workchat import service
from worknexus.modules.workchat.ai_client import (
    AIClient,
    DoneEvent,
    ErrorEvent,
    KnowledgeEvent,
    ProposeAction,
    TextDelta,
    ToolResultEvent,
)
from worknexus.modules.workchat.models import Conversation
from worknexus.modules.workchat.schemas import MessageCreateIn, MessageRole

_HISTORY_LIMIT = 20

_AI_ROLE = {MessageRole.AI: "assistant", MessageRole.USER: "user", MessageRole.SYSTEM: "system"}


@dataclass(frozen=True)
class ResolvedAgent:
    """Two distinct identities for one AI turn (WorkNexus governs AI identity; multirag runs
    the model). `internal_agent_id` is the WorkNexus `ai_agents.id` — the local security
    principal used for delegation, permission checks, AgentAction/SkillInvocation/audit
    attribution. `external_agent_id` is `ai_agents.external_agent_id` — the multirag agent id
    used in the `/api/v1/agents/{id}/completions` URL. They are never the same value in a real
    deployment."""

    internal_agent_id: str
    external_agent_id: str


async def resolve_agent(db: AsyncSession, actor: Actor, settings: Settings) -> ResolvedAgent:
    """Pick the tenant's AI agent and return both its internal and external ids.

    `WORKNEXUS_AI_PLATFORM_DEFAULT_AGENT_ID` is the multirag *external* agent id (setup stores
    it in `ai_agents.external_agent_id`). Preference: the active agent matching that external id,
    then the first active agent that has any external id, then the first active agent. Without an
    external id, real multirag cannot be called → AI_PLATFORM_UNAVAILABLE; the fake client only
    needs a placeholder, so it runs on the internal id."""
    agents = (
        (
            await db.execute(
                select(AIAgent)
                .where(AIAgent.tenant_id == actor.tenant_id, AIAgent.status == AgentStatus.ACTIVE)
                .order_by(AIAgent.created_at)
            )
        )
        .scalars()
        .all()
    )
    if not agents:
        raise BizError(ErrorCode.AI_PLATFORM_UNAVAILABLE, "no active AI agent is configured for this tenant")

    configured_external = settings.ai_platform_default_agent_id
    agent = next((a for a in agents if configured_external and a.external_agent_id == configured_external), None)
    if agent is None:
        agent = next((a for a in agents if a.external_agent_id), agents[0])

    external = agent.external_agent_id
    if not external:
        if settings.ai_client == "fake":
            external = agent.id  # the fake client ignores it; keeps tests/E2E running
        else:
            raise BizError(
                ErrorCode.AI_PLATFORM_UNAVAILABLE,
                "the AI agent has no external (multirag) agent id; set WORKNEXUS_AI_PLATFORM_DEFAULT_AGENT_ID",
            )
    return ResolvedAgent(internal_agent_id=agent.id, external_agent_id=external)


async def build_context(
    db: AsyncSession,
    subject: Subject,
    conversation: Conversation,
    *,
    work_item_ids: list[str] | None,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """D6: only data the caller can see enters the prompt. The project and any referenced
    work items pass a live permission check; conversation history is the user's own thread."""
    actor = subject.actor
    context: dict[str, Any] = {}
    project_scope = Scope(type=ScopeType.PROJECT, project_id=conversation.project_id)
    if can(subject, Permission.PROJECT_READ, project_scope):
        project = await projects_service.get_project(db, conversation.project_id, actor.tenant_id)
        context["project"] = {"id": project.id, "name": project.name, "key": project.key}

    referenced: list[dict[str, Any]] = []
    for work_item_id in work_item_ids or []:
        item = await db.get(WorkItem, work_item_id)
        if item is None or item.tenant_id != actor.tenant_id or item.deleted_at is not None:
            continue
        if not can(subject, Permission.WORK_ITEM_READ, Scope(type=ScopeType.PROJECT, project_id=item.project_id)):
            continue
        referenced.append({"id": item.id, "key": item.key, "title": item.title, "status": item.status})
    if referenced:
        context["workItems"] = referenced

    history, _ = await service.list_messages(
        db, actor, conversation.id, params=PageParams(page=1, page_size=_HISTORY_LIMIT)
    )
    messages = [{"role": _AI_ROLE.get(MessageRole(m.role), "user"), "content": m.content} for m in history]
    return messages, context


def _extract_action_id(result: Any) -> str | None:
    if isinstance(result, dict):
        value = result.get("agentActionId") or result.get("agent_action_id")
        return str(value) if value else None
    return None


async def _safe_agent_action(db: AsyncSession, actor: Actor, action_id: str) -> dict[str, Any] | None:
    try:
        out = await service.get_agent_action(db, actor, action_id)
    except BizError:
        return None
    return out.model_dump(by_alias=True, mode="json")


async def start_run(
    db: AsyncSession,
    subject: Subject,
    *,
    conversation: Conversation,
    content: str,
    work_item_ids: list[str] | None,
    ai_client: AIClient,
    agent: ResolvedAgent,
    run_id: str,
) -> AsyncIterator[dict[str, Any]]:
    """Drive one AI turn, yielding WorkNexus SSE events. Validation (conversation exists,
    permission) is done by the caller before the response starts; everything here is
    defensive — failures become an `error` event, never an aborted stream.

    Identity split: the delegation token binds the WorkNexus-internal agent id (the security
    principal), while the multirag call targets the external agent id."""
    actor = subject.actor
    await service.create_user_message(db, actor, conversation.id, MessageCreateIn(content=content))
    messages, context = await build_context(db, subject, conversation, work_item_ids=work_item_ids)

    accumulated: list[str] = []
    knowledge_refs: list[dict[str, Any]] = []
    surfaced_action_id: str | None = None
    try:
        issued = await identity_service.issue_delegation_token(
            db,
            actor,
            user_id=actor.id,
            agent_id=agent.internal_agent_id,
            project_id=conversation.project_id,
            conversation_id=conversation.id,
            run_id=run_id,
        )
        async for event in ai_client.stream_run(
            messages=messages, context=context, delegation_token=issued.token, agent_id=agent.external_agent_id
        ):
            if isinstance(event, TextDelta):
                accumulated.append(event.content)
                yield {"type": "message_delta", "content": event.content}
            elif isinstance(event, ToolResultEvent):
                action_id = _extract_action_id(event.result)
                if action_id:
                    action = await _safe_agent_action(db, actor, action_id)
                    if action is not None:
                        surfaced_action_id = surfaced_action_id or str(action["id"])
                        yield {"type": "agent_action", "action": action}
            elif isinstance(event, ProposeAction):
                # Fake/E2E only: the real path creates the action in the gated /mcp
                # middleware and surfaces it via ToolResultEvent above.
                created = await service.create_pending_agent_action(
                    db,
                    DelegationContext(
                        tenant_id=actor.tenant_id,
                        user_id=actor.id,
                        agent_id=agent.internal_agent_id,
                        project_id=conversation.project_id,
                        conversation_id=conversation.id,
                        run_id=run_id,
                        permissions_snapshot={},
                    ),
                    tool_name=event.tool_name,
                    arguments=event.arguments,
                    skill_invocation_id=None,
                )
                await db.commit()
                action = await _safe_agent_action(db, actor, created.id)
                if action is not None:
                    surfaced_action_id = surfaced_action_id or created.id
                    yield {"type": "agent_action", "action": action}
            elif isinstance(event, KnowledgeEvent):
                knowledge_refs.extend(event.references)
                yield {"type": "knowledge", "references": event.references}
            elif isinstance(event, ErrorEvent):
                yield {"type": "error", "message": event.message, "code": event.code}
            elif isinstance(event, DoneEvent):
                break
    except Exception:
        yield {"type": "error", "message": "ai run failed", "code": int(ErrorCode.AI_RUN_FAILED)}

    message = await service.create_ai_message(
        db,
        actor,
        conversation.id,
        content="".join(accumulated),
        run_id=run_id,
        agent_action_id=surfaced_action_id,
        knowledge_refs=knowledge_refs or None,
    )
    yield {"type": "message_done", "messageId": message.id}
    yield {"type": "done"}
