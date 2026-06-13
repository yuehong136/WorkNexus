from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.access import Permission, Subject, get_current_subject, require_permission
from worknexus.core.envelope import Envelope
from worknexus.core.pagination import Page, PageParamsDep
from worknexus.db import get_db
from worknexus.modules.identity import service as identity_service
from worknexus.modules.projects import service
from worknexus.modules.projects.schemas import (
    ProjectCreateIn,
    ProjectMemberAddIn,
    ProjectMemberOut,
    ProjectMemberUpdateIn,
    ProjectOut,
    ProjectStatus,
    ProjectUpdateIn,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", operation_id="list_projects")
async def list_projects(
    db: Annotated[AsyncSession, Depends(get_db)],
    params: PageParamsDep,
    subject: Annotated[Subject, Depends(get_current_subject)],
    status: ProjectStatus = ProjectStatus.ACTIVE,
) -> Envelope[Page[ProjectOut]]:
    items, total = await service.list_projects(db, subject, status=status, params=params)
    return Envelope(data=Page.build(items, total, params))


@router.post("", operation_id="create_project")
async def create_project(
    payload: ProjectCreateIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: Annotated[Subject, Depends(require_permission(Permission.PROJECT_CREATE))],
) -> Envelope[ProjectOut]:
    return Envelope(data=await service.create_project(db, subject.actor, payload))


@router.get("/{project_id}", operation_id="get_project")
async def get_project(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: Annotated[Subject, Depends(require_permission(Permission.PROJECT_READ, project_param="project_id"))],
) -> Envelope[ProjectOut]:
    return Envelope(data=await service.get_project_detail(db, subject.actor, project_id))


@router.patch("/{project_id}", operation_id="update_project")
async def update_project(
    project_id: str,
    payload: ProjectUpdateIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: Annotated[Subject, Depends(require_permission(Permission.PROJECT_UPDATE, project_param="project_id"))],
) -> Envelope[ProjectOut]:
    return Envelope(data=await service.update_project(db, subject.actor, project_id, payload))


@router.post("/{project_id}/archive", operation_id="archive_project")
async def archive_project(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: Annotated[Subject, Depends(require_permission(Permission.PROJECT_ARCHIVE, project_param="project_id"))],
) -> Envelope[ProjectOut]:
    return Envelope(data=await service.archive_project(db, subject.actor, project_id))


@router.get("/{project_id}/members", operation_id="list_project_members")
async def list_project_members(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: Annotated[Subject, Depends(require_permission(Permission.PROJECT_READ, project_param="project_id"))],
) -> Envelope[list[ProjectMemberOut]]:
    return Envelope(data=await identity_service.list_project_members(db, subject.actor, project_id))


@router.post("/{project_id}/members", operation_id="add_project_member")
async def add_project_member(
    project_id: str,
    payload: ProjectMemberAddIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: Annotated[
        Subject, Depends(require_permission(Permission.PROJECT_MEMBER_MANAGE, project_param="project_id"))
    ],
) -> Envelope[ProjectMemberOut]:
    member = await identity_service.add_project_member(db, subject.actor, project_id, payload.user_id, payload.role)
    return Envelope(data=member)


@router.patch("/{project_id}/members/{user_id}", operation_id="update_project_member")
async def update_project_member(
    project_id: str,
    user_id: str,
    payload: ProjectMemberUpdateIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: Annotated[
        Subject, Depends(require_permission(Permission.PROJECT_MEMBER_MANAGE, project_param="project_id"))
    ],
) -> Envelope[ProjectMemberOut]:
    member = await identity_service.update_project_member_role(db, subject.actor, project_id, user_id, payload.role)
    return Envelope(data=member)


@router.delete("/{project_id}/members/{user_id}", operation_id="remove_project_member")
async def remove_project_member(
    project_id: str,
    user_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: Annotated[
        Subject, Depends(require_permission(Permission.PROJECT_MEMBER_MANAGE, project_param="project_id"))
    ],
) -> Envelope[None]:
    await identity_service.remove_project_member(db, subject.actor, project_id, user_id)
    return Envelope()
