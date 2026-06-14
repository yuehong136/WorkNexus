from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from worknexus.core.schemas import ApiModel
from worknexus.modules.skills.schemas import RiskLevel

# Reuse the shared D4 risk semantics rather than redefining them.
__all__ = [
    "AgentActionOut",
    "AgentActionRejectIn",
    "AgentActionStatus",
    "AgentActionType",
    "ConversationOut",
    "MessageCreateIn",
    "MessageOut",
    "MessageRole",
    "RiskLevel",
    "RunCreateIn",
]


class MessageRole(StrEnum):
    USER = "user"
    AI = "ai"
    SYSTEM = "system"


class AgentActionType(StrEnum):
    """v0.1 confirmable write actions (the four work_items low_write tools).

    intake actions (create_intake_request / accept_intake_request) land in M6 when
    intake MCP tools exist; read tools (search / summary) execute directly, never
    becoming an AgentAction."""

    CREATE_WORK_ITEM = "create_work_item"
    UPDATE_WORK_ITEM = "update_work_item"
    TRANSITION_WORK_ITEM = "transition_work_item"
    COMMENT_WORK_ITEM = "comment_work_item"


class AgentActionStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"
    EXPIRED = "expired"


class ConversationOut(ApiModel):
    id: str
    project_id: str
    title: str | None
    kind: str
    created_by: str | None
    created_at: datetime
    updated_at: datetime


class MessageOut(ApiModel):
    id: str
    conversation_id: str
    role: MessageRole
    content: str
    run_id: str | None
    agent_action_id: str | None
    work_item_id: str | None
    knowledge_refs: list[dict[str, Any]] | None
    created_by: str | None
    created_at: datetime


class MessageCreateIn(ApiModel):
    content: str = Field(min_length=1)


class RunCreateIn(ApiModel):
    conversation_id: str
    content: str = Field(min_length=1)
    # Work items the user explicitly references; filtered by read permission before context.
    work_item_ids: list[str] | None = None


class AgentActionOut(ApiModel):
    id: str
    conversation_id: str | None
    message_id: str | None
    project_id: str
    action_type: AgentActionType
    arguments: dict[str, Any]
    risk_level: RiskLevel
    status: AgentActionStatus
    requested_by_user_id: str
    agent_id: str
    approved_by_user_id: str | None
    approved_at: datetime | None
    rejected_at: datetime | None
    executed_at: datetime | None
    rejection_reason: str | None
    skill_invocation_id: str | None
    result_ref_type: str | None
    result_ref_id: str | None
    error_message: str | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AgentActionRejectIn(ApiModel):
    reason: str | None = None
