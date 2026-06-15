from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from worknexus.core.schemas import ApiModel
from worknexus.modules.projects.schemas import UserBriefOut
from worknexus.modules.work_items.schemas import WorkItemPriority, WorkItemType

__all__ = [
    "ACTIONABLE_STATUSES",
    "TERMINAL_STATUSES",
    "IntakeAcceptIn",
    "IntakeCreateIn",
    "IntakeMarkDuplicateIn",
    "IntakeOut",
    "IntakeRejectIn",
    "IntakeSnoozeIn",
    "IntakeSource",
    "IntakeStatus",
    "IntakeUpdateIn",
]


class IntakeSource(StrEnum):
    MANUAL = "manual"
    AI_CHAT = "ai_chat"
    API = "api"
    MCP = "mcp"


class IntakeStatus(StrEnum):
    NEW = "new"
    TRIAGING = "triaging"
    # `accepted` is reserved: v0.1 accept goes straight to `converted` (single-step
    # accept-and-convert). No endpoint emits `accepted`.
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DUPLICATE = "duplicate"
    SNOOZED = "snoozed"
    CONVERTED = "converted"


# Non-terminal states a triage action (accept/reject/mark-duplicate/snooze/update) may act on.
ACTIONABLE_STATUSES = frozenset({IntakeStatus.NEW, IntakeStatus.TRIAGING, IntakeStatus.SNOOZED})
TERMINAL_STATUSES = frozenset({IntakeStatus.CONVERTED, IntakeStatus.REJECTED, IntakeStatus.DUPLICATE})


class IntakeCreateIn(ApiModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None


class IntakeUpdateIn(ApiModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    # PATCH may only nudge the in-progress marker between new and triaging.
    status: IntakeStatus | None = None


class IntakeAcceptIn(ApiModel):
    """Overrides applied to the converted work item; unset fields fall back to the AI
    suggestions, then to defaults (type=task, priority=medium)."""

    type: WorkItemType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=300)
    priority: WorkItemPriority | None = None
    assignee_id: str | None = None


class IntakeRejectIn(ApiModel):
    reason: str | None = None


class IntakeMarkDuplicateIn(ApiModel):
    duplicate_work_item_id: str


class IntakeSnoozeIn(ApiModel):
    snooze_until: datetime


class IntakeOut(ApiModel):
    id: str
    project_id: str
    title: str
    description: str | None
    source: IntakeSource
    source_ref_id: str | None
    status: IntakeStatus
    submitter_id: str | None
    ai_summary: str | None
    ai_category: str | None
    suggested_type: WorkItemType | None
    suggested_priority: WorkItemPriority | None
    suggested_assignee_id: str | None
    suggested_assignee: UserBriefOut | None
    triage_meta: dict[str, Any] | None
    duplicate_work_item_id: str | None
    converted_work_item_id: str | None
    snooze_until: datetime | None
    rejection_reason: str | None
    created_by: str | None
    updated_by: str | None
    created_at: datetime
    updated_at: datetime
