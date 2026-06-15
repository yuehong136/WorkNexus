"""Rule-based dashboard insights (M7 decision A, roadmap D7): advisory only.

A replaceable provider behind the `InsightsEngine` Protocol, mirroring M6's `TriageEngine`.
v0.1 ships `RuleBasedInsightsEngine` (deterministic, computed on demand from the already
permission-scoped aggregate metrics — no external dependency, E2E-safe); a
`MultiragInsightsEngine` slots in via `get_insights_engine` once the AI endpoint is
live-verified. Insights never trigger any write action — they are surfaced read-only on the
dashboard (advisory card), and the carried provenance (`provider`/`version`, with the service
stamping `generatedAt`) keeps a later provider switch auditable.

The rule engine returns structured signals (`kind` + `severity` + `metrics`) and leaves
`detail` prose unset — the frontend renders bilingual title/detail from i18n templates keyed on
`kind`, interpolating `metrics`. A multirag provider later fills `detail` with free prose. The
engine is time-free (the service stamps `generatedAt`) so it stays trivially unit-testable, and
it only reads aggregate counts for one project, so D6 (AI context permission filtering) holds by
construction — no individual cross-permission content.
"""

from typing import Any, Protocol

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.config import Settings
from worknexus.modules.dashboards.schemas import InsightKind, InsightSeverity
from worknexus.modules.intake.schemas import IntakeMetrics
from worknexus.modules.work_items.schemas import WorkItemMetrics, WorkItemType, WorkloadBucket

# Deterministic thresholds (documented so tests and a future tuning pass stay honest).
_OVERDUE_CRITICAL_COUNT = 10
_OVERDUE_CRITICAL_RATIO = 0.3
_HIGH_PRIORITY_CRITICAL_COUNT = 8
_RISK_TYPES = (WorkItemType.RISK, WorkItemType.INCIDENT)
_WORKLOAD_MIN_LOAD = 5  # ignore tiny projects
_WORKLOAD_IMBALANCE_FACTOR = 2.0  # top assignee load vs. average load of the others


class Insight(BaseModel):
    kind: InsightKind
    severity: InsightSeverity
    metrics: dict[str, Any]
    detail: str | None = None


class InsightInput(BaseModel):
    work_items: WorkItemMetrics
    workload: list[WorkloadBucket]
    intake: IntakeMetrics


class InsightsEngine(Protocol):
    provider: str
    version: str

    async def generate(
        self, db: AsyncSession, *, project_id: str, tenant_id: str, data: InsightInput
    ) -> list[Insight]: ...


class RuleBasedInsightsEngine:
    provider = "rules"
    version = "1"

    async def generate(self, db: AsyncSession, *, project_id: str, tenant_id: str, data: InsightInput) -> list[Insight]:
        wi = data.work_items
        insights: list[Insight] = []

        if wi.overdue_count > 0:
            ratio = wi.overdue_count / wi.total_count if wi.total_count else 0.0
            critical = wi.overdue_count >= _OVERDUE_CRITICAL_COUNT or ratio >= _OVERDUE_CRITICAL_RATIO
            insights.append(
                Insight(
                    kind=InsightKind.OVERDUE,
                    severity=InsightSeverity.CRITICAL if critical else InsightSeverity.WARNING,
                    metrics={
                        "overdueCount": wi.overdue_count,
                        "totalCount": wi.total_count,
                        "overduePercent": round(ratio * 100),
                    },
                )
            )

        if wi.high_priority_count > 0:
            critical = wi.high_priority_count >= _HIGH_PRIORITY_CRITICAL_COUNT
            insights.append(
                Insight(
                    kind=InsightKind.HIGH_PRIORITY,
                    severity=InsightSeverity.CRITICAL if critical else InsightSeverity.WARNING,
                    metrics={"highPriorityCount": wi.high_priority_count},
                )
            )

        risk_count = sum(wi.type_counts.get(str(t), 0) for t in _RISK_TYPES)
        if risk_count > 0:
            critical = wi.overdue_count > 0
            insights.append(
                Insight(
                    kind=InsightKind.RISK,
                    severity=InsightSeverity.CRITICAL if critical else InsightSeverity.WARNING,
                    metrics={
                        "riskCount": risk_count,
                        "riskTypeCount": wi.type_counts.get(str(WorkItemType.RISK), 0),
                        "incidentTypeCount": wi.type_counts.get(str(WorkItemType.INCIDENT), 0),
                    },
                )
            )

        assigned = [b for b in data.workload if b.assignee_id is not None and b.total_count > 0]
        if len(assigned) >= 2:
            top = max(assigned, key=lambda b: b.total_count)
            others = [b.total_count for b in assigned if b is not top]
            avg_others = sum(others) / len(others)
            if top.total_count >= _WORKLOAD_MIN_LOAD and top.total_count >= _WORKLOAD_IMBALANCE_FACTOR * avg_others:
                insights.append(
                    Insight(
                        kind=InsightKind.WORKLOAD,
                        severity=InsightSeverity.WARNING,
                        metrics={
                            "topAssigneeId": top.assignee_id,
                            "topAssigneeName": top.assignee.display_name if top.assignee else None,
                            "topLoad": top.total_count,
                            "averageLoad": round(sum(b.total_count for b in assigned) / len(assigned), 2),
                        },
                    )
                )

        return insights


def get_insights_engine(settings: Settings) -> InsightsEngine:
    """v0.1 only the rule engine. A `MultiragInsightsEngine` keyed on
    `settings.dashboard_insights_provider` slots in here after the AI endpoint is live-verified."""
    return RuleBasedInsightsEngine()
