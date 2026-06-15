from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.access import Permission, Subject, require_permission
from worknexus.core.envelope import Envelope
from worknexus.core.pagination import Page, PageParamsDep
from worknexus.db import get_db
from worknexus.modules.intake import service
from worknexus.modules.intake.deps import require_intake_permission
from worknexus.modules.intake.schemas import (
    IntakeAcceptIn,
    IntakeCreateIn,
    IntakeMarkDuplicateIn,
    IntakeOut,
    IntakeRejectIn,
    IntakeSnoozeIn,
    IntakeSource,
    IntakeStatus,
    IntakeUpdateIn,
)

router = APIRouter(tags=["intake"])


@router.get("/projects/{project_id}/intake", operation_id="list_intake")
async def list_intake(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    params: PageParamsDep,
    subject: Annotated[Subject, Depends(require_permission(Permission.INTAKE_READ, project_param="project_id"))],
    status: IntakeStatus | None = None,
    source: IntakeSource | None = None,
) -> Envelope[Page[IntakeOut]]:
    items, total = await service.list_intake_requests(
        db, subject.actor, project_id, status=status, source=source, params=params
    )
    return Envelope(data=Page.build(items, total, params))


@router.post("/projects/{project_id}/intake", operation_id="create_intake")
async def create_intake(
    project_id: str,
    payload: IntakeCreateIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: Annotated[Subject, Depends(require_permission(Permission.INTAKE_CREATE, project_param="project_id"))],
) -> Envelope[IntakeOut]:
    return Envelope(data=await service.create_intake_request(db, subject.actor, project_id, payload))


@router.get("/intake/{intake_id}", operation_id="get_intake")
async def get_intake(
    intake_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: Annotated[Subject, Depends(require_intake_permission(Permission.INTAKE_READ))],
) -> Envelope[IntakeOut]:
    return Envelope(data=await service.get_intake_request(db, subject.actor, intake_id))


@router.patch("/intake/{intake_id}", operation_id="update_intake")
async def update_intake(
    intake_id: str,
    payload: IntakeUpdateIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: Annotated[Subject, Depends(require_intake_permission(Permission.INTAKE_TRIAGE))],
) -> Envelope[IntakeOut]:
    return Envelope(data=await service.update_intake_request(db, subject.actor, intake_id, payload))


@router.post("/intake/{intake_id}/accept", operation_id="accept_intake")
async def accept_intake(
    intake_id: str,
    payload: IntakeAcceptIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: Annotated[Subject, Depends(require_intake_permission(Permission.INTAKE_TRIAGE))],
) -> Envelope[IntakeOut]:
    return Envelope(data=await service.accept_intake_request(db, subject.actor, intake_id, payload))


@router.post("/intake/{intake_id}/reject", operation_id="reject_intake")
async def reject_intake(
    intake_id: str,
    payload: IntakeRejectIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: Annotated[Subject, Depends(require_intake_permission(Permission.INTAKE_TRIAGE))],
) -> Envelope[IntakeOut]:
    return Envelope(data=await service.reject_intake_request(db, subject.actor, intake_id, payload.reason))


@router.post("/intake/{intake_id}/mark-duplicate", operation_id="mark_intake_duplicate")
async def mark_intake_duplicate(
    intake_id: str,
    payload: IntakeMarkDuplicateIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: Annotated[Subject, Depends(require_intake_permission(Permission.INTAKE_TRIAGE))],
) -> Envelope[IntakeOut]:
    return Envelope(data=await service.mark_duplicate(db, subject.actor, intake_id, payload.duplicate_work_item_id))


@router.post("/intake/{intake_id}/snooze", operation_id="snooze_intake")
async def snooze_intake(
    intake_id: str,
    payload: IntakeSnoozeIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: Annotated[Subject, Depends(require_intake_permission(Permission.INTAKE_TRIAGE))],
) -> Envelope[IntakeOut]:
    return Envelope(data=await service.snooze_intake_request(db, subject.actor, intake_id, payload.snooze_until))
