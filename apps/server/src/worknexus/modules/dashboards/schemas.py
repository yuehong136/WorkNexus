from datetime import datetime
from enum import StrEnum
from typing import Any

from worknexus.core.schemas import ApiModel
from worknexus.modules.projects.schemas import UserBriefOut
from worknexus.modules.work_items.schemas import (
    WorkItemPriority,
    WorkItemSource,
    WorkItemStatus,
    WorkItemType,
)


class TrendPoint(ApiModel):
    date: str  # UTC date, ISO `YYYY-MM-DD`
    count: int


class DashboardSummaryOut(ApiModel):
    total_count: int
    status_counts: dict[str, int]
    type_counts: dict[str, int]
    priority_counts: dict[str, int]
    source_counts: dict[str, int]
    high_priority_count: int
    overdue_count: int
    ai_created_count: int  # source in (ai_chat, mcp) — matches M3 project summary
    intake_request_count: int
    intake_status_counts: dict[str, int]
    intake_converted_count: int
    intake_conversion_rate: float
    created_trend: list[TrendPoint]
    completed_trend: list[TrendPoint]


class WorkloadItemOut(ApiModel):
    assignee_id: str | None  # None = unassigned bucket
    assignee: UserBriefOut | None
    total_count: int
    status_counts: dict[str, int]
    overdue_count: int
    high_priority_count: int


class DashboardWorkloadOut(ApiModel):
    items: list[WorkloadItemOut]


class DashboardOverdueItemOut(ApiModel):
    id: str
    key: str
    title: str
    status: WorkItemStatus
    type: WorkItemType
    priority: WorkItemPriority
    assignee_id: str | None
    assignee: UserBriefOut | None
    due_at: datetime
    days_overdue: int
    source: WorkItemSource
    created_at: datetime


class InsightKind(StrEnum):
    RISK = "risk"
    OVERDUE = "overdue"
    HIGH_PRIORITY = "high_priority"
    WORKLOAD = "workload"


class InsightSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class InsightOut(ApiModel):
    kind: InsightKind
    severity: InsightSeverity
    metrics: dict[str, Any]  # supporting numbers; the frontend localizes title/detail from these
    # Optional advisory prose. Null for the v0.1 rule engine (the frontend renders localized
    # text from `kind` + `metrics`); the slot a multirag provider fills later with free prose.
    detail: str | None = None


class InsightProvenance(ApiModel):
    provider: str
    version: str
    generated_at: datetime


class DashboardInsightsOut(ApiModel):
    insights: list[InsightOut]
    provenance: InsightProvenance
