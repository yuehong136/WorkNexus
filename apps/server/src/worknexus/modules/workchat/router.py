from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.access import Permission, Subject, require_permission
from worknexus.core.envelope import Envelope
from worknexus.core.pagination import Page, PageParamsDep
from worknexus.db import get_db
from worknexus.modules.workchat import service
from worknexus.modules.workchat.deps import (
    accessible_project_ids,
    require_agent_action_permission,
    require_conversation_permission,
)
from worknexus.modules.workchat.schemas import (
    AgentActionOut,
    AgentActionRejectIn,
    AgentActionStatus,
    ConversationOut,
    MessageCreateIn,
    MessageOut,
)

router = APIRouter(tags=["workchat"])


@router.get("/projects/{project_id}/conversations", operation_id="list_conversations")
async def list_conversations(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: Annotated[Subject, Depends(require_permission(Permission.WORKCHAT_USE, project_param="project_id"))],
) -> Envelope[list[ConversationOut]]:
    return Envelope(data=await service.list_conversations(db, subject.actor, project_id))


@router.get("/conversations/{conversation_id}/messages", operation_id="list_messages")
async def list_messages(
    conversation_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    params: PageParamsDep,
    subject: Annotated[Subject, Depends(require_conversation_permission(Permission.WORKCHAT_USE))],
) -> Envelope[Page[MessageOut]]:
    items, total = await service.list_messages(db, subject.actor, conversation_id, params=params)
    return Envelope(data=Page.build(items, total, params))


@router.post("/conversations/{conversation_id}/messages", operation_id="create_message")
async def create_message(
    conversation_id: str,
    payload: MessageCreateIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: Annotated[Subject, Depends(require_conversation_permission(Permission.WORKCHAT_USE))],
) -> Envelope[MessageOut]:
    return Envelope(data=await service.create_user_message(db, subject.actor, conversation_id, payload))


@router.get("/agent-actions", operation_id="list_agent_actions")
async def list_agent_actions(
    db: Annotated[AsyncSession, Depends(get_db)],
    params: PageParamsDep,
    subject: Annotated[Subject, Depends(require_permission(Permission.WORKCHAT_USE))],
    status: AgentActionStatus | None = None,
    project_id: str | None = None,
) -> Envelope[Page[AgentActionOut]]:
    items, total = await service.list_agent_actions(
        db,
        subject.actor,
        accessible_project_ids=accessible_project_ids(subject),
        params=params,
        status=status,
        project_id=project_id,
    )
    return Envelope(data=Page.build(items, total, params))


@router.get("/agent-actions/{agent_action_id}", operation_id="get_agent_action")
async def get_agent_action(
    agent_action_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: Annotated[Subject, Depends(require_agent_action_permission(Permission.WORKCHAT_USE))],
) -> Envelope[AgentActionOut]:
    return Envelope(data=await service.get_agent_action(db, subject.actor, agent_action_id))


@router.post("/agent-actions/{agent_action_id}/approve", operation_id="approve_agent_action")
async def approve_agent_action(
    agent_action_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: Annotated[Subject, Depends(require_agent_action_permission(Permission.AGENT_ACTION_CONFIRM))],
) -> Envelope[AgentActionOut]:
    return Envelope(data=await service.approve_and_execute(db, subject.actor, agent_action_id))


@router.post("/agent-actions/{agent_action_id}/reject", operation_id="reject_agent_action")
async def reject_agent_action(
    agent_action_id: str,
    payload: AgentActionRejectIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: Annotated[Subject, Depends(require_agent_action_permission(Permission.AGENT_ACTION_CONFIRM))],
) -> Envelope[AgentActionOut]:
    return Envelope(data=await service.reject(db, subject.actor, agent_action_id, payload.reason))
