from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.access import Permission, Subject, require_permission
from worknexus.core.envelope import Envelope
from worknexus.core.pagination import Page, PageParamsDep
from worknexus.db import get_db
from worknexus.modules.dashboards import service
from worknexus.modules.dashboards.schemas import (
    DashboardInsightsOut,
    DashboardOverdueItemOut,
    DashboardSummaryOut,
    DashboardWorkloadOut,
)

router = APIRouter(tags=["dashboard"])

_DashboardSubject = Annotated[
    Subject, Depends(require_permission(Permission.DASHBOARD_READ, project_param="project_id"))
]


@router.get("/projects/{project_id}/dashboard/summary", operation_id="get_dashboard_summary")
async def get_dashboard_summary(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: _DashboardSubject,
) -> Envelope[DashboardSummaryOut]:
    return Envelope(data=await service.get_dashboard_summary(db, subject.actor, project_id))


@router.get("/projects/{project_id}/dashboard/workload", operation_id="get_dashboard_workload")
async def get_dashboard_workload(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: _DashboardSubject,
) -> Envelope[DashboardWorkloadOut]:
    return Envelope(data=await service.get_dashboard_workload(db, subject.actor, project_id))


@router.get("/projects/{project_id}/dashboard/overdue", operation_id="get_dashboard_overdue")
async def get_dashboard_overdue(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    params: PageParamsDep,
    subject: _DashboardSubject,
) -> Envelope[Page[DashboardOverdueItemOut]]:
    return Envelope(data=await service.get_dashboard_overdue(db, subject.actor, project_id, params))


@router.get("/projects/{project_id}/dashboard/ai-insights", operation_id="get_dashboard_ai_insights")
async def get_dashboard_ai_insights(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: _DashboardSubject,
) -> Envelope[DashboardInsightsOut]:
    return Envelope(data=await service.get_dashboard_insights(db, subject.actor, project_id))
