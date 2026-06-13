from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from worknexus.core.schemas import ApiModel
from worknexus.modules.projects.schemas import UserBriefOut


class WorkItemType(StrEnum):
    TASK = "task"
    REQUIREMENT = "requirement"
    BUG = "bug"
    RISK = "risk"
    DECISION = "decision"
    APPROVAL = "approval"
    INCIDENT = "incident"
    FEEDBACK = "feedback"


class WorkItemStatus(StrEnum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    CANCELLED = "cancelled"


class WorkItemPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class WorkItemSource(StrEnum):
    MANUAL = "manual"
    AI_CHAT = "ai_chat"
    INTAKE = "intake"
    MCP = "mcp"
    API = "api"


class RelationType(StrEnum):
    PARENT_CHILD = "parent_child"
    BLOCKS = "blocks"
    BLOCKED_BY = "blocked_by"
    DUPLICATES = "duplicates"
    RELATES_TO = "relates_to"
    CREATED_FROM_MESSAGE = "created_from_message"
    CREATED_FROM_INTAKE = "created_from_intake"


class ActivityAction(StrEnum):
    CREATED = "created"
    TITLE_CHANGED = "title_changed"
    DESCRIPTION_CHANGED = "description_changed"
    ASSIGNEE_CHANGED = "assignee_changed"
    PRIORITY_CHANGED = "priority_changed"
    STATUS_CHANGED = "status_changed"
    COMMENTED = "commented"
    RELATION_ADDED = "relation_added"
    RELATION_REMOVED = "relation_removed"
    DELETED = "deleted"


class CommentAuthorType(StrEnum):
    USER = "user"
    AI_AGENT = "ai_agent"
    SYSTEM = "system"


class WorkItemSort(StrEnum):
    CREATED_DESC = "created_desc"
    CREATED_ASC = "created_asc"
    UPDATED_DESC = "updated_desc"
    UPDATED_ASC = "updated_asc"


# Fixed state machine (spec §3): forward path + review→in_progress backward edge + any-non-done→cancelled.
ALLOWED_TRANSITIONS: dict[WorkItemStatus, frozenset[WorkItemStatus]] = {
    WorkItemStatus.BACKLOG: frozenset({WorkItemStatus.TODO, WorkItemStatus.CANCELLED}),
    WorkItemStatus.TODO: frozenset({WorkItemStatus.IN_PROGRESS, WorkItemStatus.CANCELLED}),
    WorkItemStatus.IN_PROGRESS: frozenset({WorkItemStatus.REVIEW, WorkItemStatus.CANCELLED}),
    WorkItemStatus.REVIEW: frozenset({WorkItemStatus.DONE, WorkItemStatus.IN_PROGRESS, WorkItemStatus.CANCELLED}),
    WorkItemStatus.DONE: frozenset(),
    WorkItemStatus.CANCELLED: frozenset(),
}


# --- type-specific custom fields (decision B: backend light validation, extra forbidden) ---


class _CustomFields(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BugFields(_CustomFields):
    severity: str | None = None
    steps_to_reproduce: str | None = None
    expected_result: str | None = None
    actual_result: str | None = None
    environment: str | None = None
    affected_version: str | None = None


class RequirementFields(_CustomFields):
    business_goal: str | None = None
    user_value: str | None = None
    boundary_conditions: str | None = None
    dependencies: str | None = None


class RiskFields(_CustomFields):
    risk_level: str | None = None
    impact: str | None = None
    probability: str | None = None
    mitigation_plan: str | None = None
    trigger_condition: str | None = None


class DecisionFields(_CustomFields):
    background: str | None = None
    options: str | None = None
    decision_result: str | None = None
    decision_owner: str | None = None
    impact_scope: str | None = None


class ApprovalFields(_CustomFields):
    approval_type: str | None = None
    approvers: list[str] | None = None
    approval_status: str | None = None
    approval_comment: str | None = None


CUSTOM_FIELD_SCHEMAS: dict[WorkItemType, type[_CustomFields]] = {
    WorkItemType.TASK: _CustomFields,
    WorkItemType.INCIDENT: _CustomFields,
    WorkItemType.FEEDBACK: _CustomFields,
    WorkItemType.BUG: BugFields,
    WorkItemType.REQUIREMENT: RequirementFields,
    WorkItemType.RISK: RiskFields,
    WorkItemType.DECISION: DecisionFields,
    WorkItemType.APPROVAL: ApprovalFields,
}


# --- request / response schemas ---


class WorkItemCreateIn(ApiModel):
    type: WorkItemType
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    priority: WorkItemPriority = WorkItemPriority.MEDIUM
    assignee_id: str | None = None
    due_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    acceptance_criteria: str | None = None
    custom_fields: dict[str, Any] = Field(default_factory=dict)


class WorkItemUpdateIn(ApiModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    priority: WorkItemPriority | None = None
    assignee_id: str | None = None
    due_at: datetime | None = None
    tags: list[str] | None = None
    ai_summary: str | None = None
    acceptance_criteria: str | None = None
    custom_fields: dict[str, Any] | None = None


class WorkItemTransitionIn(ApiModel):
    status: WorkItemStatus


class WorkItemOut(ApiModel):
    id: str
    key: str
    project_id: str
    seq: int
    type: WorkItemType
    title: str
    description: str | None
    status: WorkItemStatus
    priority: WorkItemPriority
    assignee_id: str | None
    assignee: UserBriefOut | None
    reporter_id: str | None
    due_at: datetime | None
    tags: list[str]
    source: WorkItemSource
    source_ref_id: str | None
    ai_summary: str | None
    acceptance_criteria: str | None
    custom_fields: dict[str, Any]
    created_by: str | None
    updated_by: str | None
    created_at: datetime
    updated_at: datetime
