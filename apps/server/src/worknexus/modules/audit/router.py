from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.access import Permission, Subject, require_permission
from worknexus.core.envelope import Envelope
from worknexus.core.pagination import Page, PageParamsDep
from worknexus.db import get_db
from worknexus.modules.audit import service
from worknexus.modules.audit.schemas import AuditActorType, AuditLogOut
from worknexus.modules.audit.service import AuditAction

router = APIRouter(tags=["audit"])


@router.get("/audit-logs", operation_id="list_audit_logs")
async def list_audit_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    params: PageParamsDep,
    subject: Annotated[Subject, Depends(require_permission(Permission.AUDIT_READ))],
    actor_type: AuditActorType | None = None,
    actor_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    project_id: str | None = None,
    action: AuditAction | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> Envelope[Page[AuditLogOut]]:
    items, total = await service.list_audit_logs(
        db,
        subject.actor,
        params=params,
        actor_type=actor_type,
        actor_id=actor_id,
        resource_type=resource_type,
        resource_id=resource_id,
        project_id=project_id,
        action=action,
        created_from=created_from,
        created_to=created_to,
    )
    return Envelope(data=Page.build(items, total, params))
