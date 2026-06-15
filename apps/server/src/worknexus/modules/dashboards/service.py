"""dashboards service: read facade + insight layer (M7).

Read-only and side-effect-free — no commit, no audit, no AgentAction. It orchestrates the
domain metrics read-models owned by `work_items` and `intake` (decision B) and assembles the
REST DTOs; it never imports those modules' models. AI insights are generated on demand by the
rule-based `InsightsEngine` (decision A) and carry provenance.
"""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.config import get_settings
from worknexus.core.deps import Actor
from worknexus.core.pagination import Page, PageParams
from worknexus.modules.dashboards.insights import InsightInput, get_insights_engine
from worknexus.modules.dashboards.schemas import (
    DashboardInsightsOut,
    DashboardOverdueItemOut,
    DashboardSnapshotOut,
    DashboardSummaryOut,
    DashboardWorkloadOut,
    InsightOut,
    InsightProvenance,
    TrendPoint,
    WorkloadItemOut,
)
from worknexus.modules.intake import service as intake_service
from worknexus.modules.work_items import service as work_items_service


def _now() -> datetime:
    return datetime.now(UTC)


async def get_dashboard_summary(db: AsyncSession, actor: Actor, project_id: str) -> DashboardSummaryOut:
    wi = await work_items_service.get_project_work_item_metrics(db, actor, project_id)
    intake = await intake_service.get_project_intake_metrics(db, actor, project_id)
    return DashboardSummaryOut(
        total_count=wi.total_count,
        status_counts=wi.status_counts,
        type_counts=wi.type_counts,
        priority_counts=wi.priority_counts,
        source_counts=wi.source_counts,
        high_priority_count=wi.high_priority_count,
        overdue_count=wi.overdue_count,
        ai_created_count=wi.ai_created_count,
        intake_request_count=intake.request_count,
        intake_status_counts=intake.status_counts,
        intake_converted_count=intake.converted_count,
        intake_conversion_rate=intake.conversion_rate,
        created_trend=[TrendPoint(date=p.date, count=p.count) for p in wi.created_trend],
        completed_trend=[TrendPoint(date=p.date, count=p.count) for p in wi.completed_trend],
    )


async def get_dashboard_workload(db: AsyncSession, actor: Actor, project_id: str) -> DashboardWorkloadOut:
    buckets = await work_items_service.get_project_workload_metrics(db, actor, project_id)
    return DashboardWorkloadOut(items=[WorkloadItemOut.model_validate(b) for b in buckets])


async def get_dashboard_overdue(
    db: AsyncSession, actor: Actor, project_id: str, params: PageParams
) -> Page[DashboardOverdueItemOut]:
    rows, total = await work_items_service.list_project_overdue_work_items(db, actor, project_id, params)
    items = [DashboardOverdueItemOut.model_validate(r) for r in rows]
    return Page.build(items, total, params)


async def get_dashboard_insights(db: AsyncSession, actor: Actor, project_id: str) -> DashboardInsightsOut:
    wi = await work_items_service.get_project_work_item_metrics(db, actor, project_id)
    workload = await work_items_service.get_project_workload_metrics(db, actor, project_id)
    intake = await intake_service.get_project_intake_metrics(db, actor, project_id)
    engine = get_insights_engine(get_settings())
    insights = await engine.generate(
        db,
        project_id=project_id,
        tenant_id=actor.tenant_id,
        data=InsightInput(work_items=wi, workload=workload, intake=intake),
    )
    return DashboardInsightsOut(
        insights=[InsightOut.model_validate(i) for i in insights],
        provenance=InsightProvenance(provider=engine.provider, version=engine.version, generated_at=_now()),
    )


async def get_project_dashboard_snapshot(
    db: AsyncSession, actor: Actor, project_id: str, *, overdue_limit: int = 10
) -> DashboardSnapshotOut:
    """One read-only bundle for the MCP tool: summary + workload + capped overdue preview +
    rule insights. Composes the same domain read-models; overdue is a top-N preview here."""
    summary = await get_dashboard_summary(db, actor, project_id)
    workload = await get_dashboard_workload(db, actor, project_id)
    insights = await get_dashboard_insights(db, actor, project_id)
    rows, total = await work_items_service.list_project_overdue_work_items(
        db, actor, project_id, PageParams(page=1, page_size=overdue_limit)
    )
    return DashboardSnapshotOut(
        summary=summary,
        workload=workload.items,
        overdue_count=total,
        overdue_preview=[DashboardOverdueItemOut.model_validate(r) for r in rows],
        insights=insights,
    )
