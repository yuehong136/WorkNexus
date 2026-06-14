from datetime import datetime
from enum import StrEnum

from worknexus.core.access import Permission
from worknexus.core.schemas import ApiModel


class RiskLevel(StrEnum):
    """AI action risk (D4). Shared semantics with MCP tags / AgentAction (M5)."""

    READ = "read"
    LOW_WRITE = "low_write"
    HIGH_WRITE = "high_write"


class SkillInvocationStatus(StrEnum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"
    REJECTED = "rejected"


class RepresentedUserOut(ApiModel):
    id: str
    display_name: str


class SkillInvocationOut(ApiModel):
    id: str
    skill_code: str
    tool_name: str
    caller_type: str
    caller_id: str
    represented_user_id: str
    represented_user: RepresentedUserOut | None = None
    agent_id: str
    project_id: str | None
    conversation_id: str | None
    run_id: str | None
    input_summary: str
    output_summary: str | None
    status: SkillInvocationStatus
    risk_level: RiskLevel
    requires_confirmation: bool
    agent_action_id: str | None
    audit_log_id: str | None
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None
    created_at: datetime


class SkillToolOut(ApiModel):
    tool_name: str
    risk_level: RiskLevel | None
    executable_in_v01: bool
    required_permission: Permission | None


class SkillOut(ApiModel):
    skill_code: str
    tools: list[SkillToolOut]
