from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from worknexus.db import Base, EntityMixin


class SkillInvocation(EntityMixin, Base):
    """One row per MCP tool call (success / failure / blocked / rejected all recorded).

    Identity columns come from the delegation token, never from tool parameters.
    `agent_action_id` stays null until M5 adds the AgentAction confirmation flow.
    """

    __tablename__ = "skill_invocations"
    __table_args__ = (Index("ix_skill_invocations_tenant_created", "tenant_id", "created_at"),)

    skill_code: Mapped[str] = mapped_column(String(50))
    tool_name: Mapped[str] = mapped_column(String(100), index=True)
    caller_type: Mapped[str] = mapped_column(String(20))
    caller_id: Mapped[str] = mapped_column(String(32))
    represented_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("ai_agents.id"))
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"))
    conversation_id: Mapped[str | None] = mapped_column(String(64))
    run_id: Mapped[str | None] = mapped_column(String(64))
    input_summary: Mapped[str] = mapped_column(Text)
    output_summary: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20))
    risk_level: Mapped[str] = mapped_column(String(20))
    requires_confirmation: Mapped[bool] = mapped_column(Boolean)
    agent_action_id: Mapped[str | None] = mapped_column(String(32))
    audit_log_id: Mapped[str | None] = mapped_column(ForeignKey("audit_logs.id"))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column()
    finished_at: Mapped[datetime | None] = mapped_column()
