from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from worknexus.db import Base, EntityMixin


class Conversation(EntityMixin, Base):
    """One AI chat thread. v0.1 keeps a single default conversation per project."""

    __tablename__ = "conversations"
    __table_args__ = (Index("ix_conversations_tenant_project", "tenant_id", "project_id"),)

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    title: Mapped[str | None] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20), default="default")
    created_by: Mapped[str | None] = mapped_column(String(32))
    deleted_at: Mapped[datetime | None] = mapped_column()


class Message(EntityMixin, Base):
    """A user / ai / system turn. May link to the AgentAction it proposed and the
    work item that action touched. `agent_action_id` / `work_item_id` are populated
    by the M5 run flow; user messages carry neither."""

    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_conversation_created", "conversation_id", "created_at"),)

    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(10))
    content: Mapped[str] = mapped_column(Text)
    run_id: Mapped[str | None] = mapped_column(String(64))
    agent_action_id: Mapped[str | None] = mapped_column(ForeignKey("agent_actions.id"))
    work_item_id: Mapped[str | None] = mapped_column(ForeignKey("work_items.id"))
    knowledge_refs: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    created_by: Mapped[str | None] = mapped_column(String(32))


class AgentAction(EntityMixin, Base):
    """A normalized, audited pending write proposed by the AI via a low_write MCP tool.

    The skills middleware creates it (status=pending) instead of executing the tool; a
    user later approves it, the dispatcher runs the real work_items.service write under a
    fresh live double-check. `permissions_snapshot` is proposal-time evidence only — it
    never substitutes for the live check at approval."""

    __tablename__ = "agent_actions"
    __table_args__ = (
        Index("ix_agent_actions_tenant_status_created", "tenant_id", "status", "created_at"),
        Index("ix_agent_actions_project_status", "project_id", "status"),
    )

    conversation_id: Mapped[str | None] = mapped_column(ForeignKey("conversations.id", ondelete="SET NULL"))
    # Plain reference (no FK) to break the messages <-> agent_actions cycle; the
    # authoritative link is messages.agent_action_id.
    message_id: Mapped[str | None] = mapped_column(String(32))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    action_type: Mapped[str] = mapped_column(String(64))
    arguments: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    risk_level: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), index=True)
    requested_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    agent_id: Mapped[str] = mapped_column(ForeignKey("ai_agents.id"))
    approved_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column()
    rejected_at: Mapped[datetime | None] = mapped_column()
    executed_at: Mapped[datetime | None] = mapped_column()
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    permissions_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    # Plain reference, not an FK, to avoid a circular FK with skill_invocations
    # (skill_invocations.agent_action_id points back here).
    skill_invocation_id: Mapped[str | None] = mapped_column(String(32))
    result_ref_type: Mapped[str | None] = mapped_column(String(32))
    result_ref_id: Mapped[str | None] = mapped_column(String(32))
    error_message: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column()
    created_by: Mapped[str | None] = mapped_column(String(32))
    updated_by: Mapped[str | None] = mapped_column(String(32))
