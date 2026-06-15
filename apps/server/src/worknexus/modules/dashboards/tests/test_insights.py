"""RuleBasedInsightsEngine: deterministic, time-free signals from aggregate metrics."""

from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.modules.dashboards.insights import Insight, InsightInput, RuleBasedInsightsEngine
from worknexus.modules.dashboards.schemas import InsightKind, InsightSeverity
from worknexus.modules.intake.schemas import IntakeMetrics
from worknexus.modules.work_items.schemas import WorkItemMetrics, WorkloadBucket

pytestmark = pytest.mark.p1

_ENGINE = RuleBasedInsightsEngine()


def _wi(**overrides: Any) -> WorkItemMetrics:
    base: dict[str, Any] = {
        "total_count": 0,
        "status_counts": {},
        "type_counts": {},
        "priority_counts": {},
        "source_counts": {},
        "high_priority_count": 0,
        "overdue_count": 0,
        "ai_created_count": 0,
        "created_trend": [],
        "completed_trend": [],
    }
    base.update(overrides)
    return WorkItemMetrics(**base)


def _intake() -> IntakeMetrics:
    return IntakeMetrics(request_count=0, status_counts={}, converted_count=0, conversion_rate=0.0)


async def _run(
    db: AsyncSession, *, work_items: WorkItemMetrics, workload: list[WorkloadBucket] | None = None
) -> dict[InsightKind, Insight]:
    data = InsightInput(work_items=work_items, workload=workload or [], intake=_intake())
    insights = await _ENGINE.generate(db, project_id="p", tenant_id="t", data=data)
    return {i.kind: i for i in insights}


async def test_no_signals_yields_no_insights(db: AsyncSession) -> None:
    by_kind = await _run(db, work_items=_wi(total_count=3, status_counts={"backlog": 3}))
    assert by_kind == {}


async def test_overdue_warning_then_critical(db: AsyncSession) -> None:
    warn = await _run(db, work_items=_wi(total_count=100, overdue_count=2))
    assert warn[InsightKind.OVERDUE].severity == InsightSeverity.WARNING
    assert warn[InsightKind.OVERDUE].metrics["overdueCount"] == 2

    # critical by absolute count
    crit = await _run(db, work_items=_wi(total_count=100, overdue_count=10))
    assert crit[InsightKind.OVERDUE].severity == InsightSeverity.CRITICAL

    # critical by ratio (>= 30%)
    ratio = await _run(db, work_items=_wi(total_count=5, overdue_count=2))
    assert ratio[InsightKind.OVERDUE].severity == InsightSeverity.CRITICAL


async def test_high_priority_threshold(db: AsyncSession) -> None:
    warn = await _run(db, work_items=_wi(total_count=10, high_priority_count=3))
    assert warn[InsightKind.HIGH_PRIORITY].severity == InsightSeverity.WARNING
    crit = await _run(db, work_items=_wi(total_count=10, high_priority_count=8))
    assert crit[InsightKind.HIGH_PRIORITY].severity == InsightSeverity.CRITICAL


async def test_risk_insight_escalates_with_overdue(db: AsyncSession) -> None:
    warn = await _run(db, work_items=_wi(total_count=5, type_counts={"risk": 1, "incident": 1}))
    assert warn[InsightKind.RISK].severity == InsightSeverity.WARNING
    assert warn[InsightKind.RISK].metrics["riskCount"] == 2

    crit = await _run(db, work_items=_wi(total_count=5, overdue_count=1, type_counts={"incident": 1}))
    assert crit[InsightKind.RISK].severity == InsightSeverity.CRITICAL


async def test_workload_imbalance(db: AsyncSession) -> None:
    balanced = [
        WorkloadBucket(
            assignee_id="a", assignee=None, total_count=3, status_counts={}, overdue_count=0, high_priority_count=0
        ),
        WorkloadBucket(
            assignee_id="b", assignee=None, total_count=3, status_counts={}, overdue_count=0, high_priority_count=0
        ),
    ]
    assert InsightKind.WORKLOAD not in await _run(db, work_items=_wi(total_count=6), workload=balanced)

    skewed = [
        WorkloadBucket(
            assignee_id="a", assignee=None, total_count=8, status_counts={}, overdue_count=0, high_priority_count=0
        ),
        WorkloadBucket(
            assignee_id="b", assignee=None, total_count=1, status_counts={}, overdue_count=0, high_priority_count=0
        ),
        # unassigned bucket is ignored for imbalance
        WorkloadBucket(
            assignee_id=None, assignee=None, total_count=20, status_counts={}, overdue_count=0, high_priority_count=0
        ),
    ]
    by_kind = await _run(db, work_items=_wi(total_count=29), workload=skewed)
    assert by_kind[InsightKind.WORKLOAD].metrics["topAssigneeId"] == "a"
    assert by_kind[InsightKind.WORKLOAD].metrics["topLoad"] == 8


def test_provider_version() -> None:
    assert _ENGINE.provider == "rules"
    assert _ENGINE.version == "1"
