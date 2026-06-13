from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.access import Permission, Subject, require_permission
from worknexus.core.envelope import Envelope
from worknexus.core.pagination import Page, PageParamsDep
from worknexus.db import get_db
from worknexus.modules.work_items import service
from worknexus.modules.work_items.deps import require_work_item_permission
from worknexus.modules.work_items.schemas import (
    WorkItemCreateIn,
    WorkItemOut,
    WorkItemPriority,
    WorkItemSort,
    WorkItemStatus,
    WorkItemTransitionIn,
    WorkItemType,
    WorkItemUpdateIn,
)

router = APIRouter(tags=["work-items"])


@router.get("/projects/{project_id}/work-items", operation_id="list_work_items")
async def list_work_items(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    params: PageParamsDep,
    subject: Annotated[Subject, Depends(require_permission(Permission.WORK_ITEM_READ, project_param="project_id"))],
    status: WorkItemStatus | None = None,
    type: WorkItemType | None = None,
    priority: WorkItemPriority | None = None,
    assignee_id: str | None = None,
    sort: WorkItemSort = WorkItemSort.CREATED_DESC,
) -> Envelope[Page[WorkItemOut]]:
    items, total = await service.list_work_items(
        db,
        subject.actor,
        project_id,
        status=status,
        type=type,
        priority=priority,
        assignee_id=assignee_id,
        sort=sort,
        params=params,
    )
    return Envelope(data=Page.build(items, total, params))


@router.post("/projects/{project_id}/work-items", operation_id="create_work_item")
async def create_work_item(
    project_id: str,
    payload: WorkItemCreateIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: Annotated[Subject, Depends(require_permission(Permission.WORK_ITEM_CREATE, project_param="project_id"))],
) -> Envelope[WorkItemOut]:
    return Envelope(data=await service.create_work_item(db, subject.actor, project_id, payload))


@router.get("/work-items/{work_item_id}", operation_id="get_work_item")
async def get_work_item(
    work_item_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: Annotated[Subject, Depends(require_work_item_permission(Permission.WORK_ITEM_READ))],
) -> Envelope[WorkItemOut]:
    return Envelope(data=await service.get_work_item_detail(db, subject.actor, work_item_id))


@router.patch("/work-items/{work_item_id}", operation_id="update_work_item")
async def update_work_item(
    work_item_id: str,
    payload: WorkItemUpdateIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: Annotated[Subject, Depends(require_work_item_permission(Permission.WORK_ITEM_UPDATE))],
) -> Envelope[WorkItemOut]:
    return Envelope(data=await service.update_work_item(db, subject.actor, work_item_id, payload))


@router.delete("/work-items/{work_item_id}", operation_id="delete_work_item")
async def delete_work_item(
    work_item_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: Annotated[Subject, Depends(require_work_item_permission(Permission.WORK_ITEM_DELETE))],
) -> Envelope[None]:
    await service.delete_work_item(db, subject.actor, work_item_id)
    return Envelope()


@router.post("/work-items/{work_item_id}/transition", operation_id="transition_work_item")
async def transition_work_item(
    work_item_id: str,
    payload: WorkItemTransitionIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: Annotated[Subject, Depends(require_work_item_permission(Permission.WORK_ITEM_TRANSITION))],
) -> Envelope[WorkItemOut]:
    return Envelope(data=await service.transition_work_item(db, subject.actor, work_item_id, payload))
