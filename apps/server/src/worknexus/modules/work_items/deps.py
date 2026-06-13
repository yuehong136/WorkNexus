from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.access import Permission, Scope, ScopeType, Subject, can, get_current_subject
from worknexus.core.errors import BizError, ErrorCode
from worknexus.db import get_db
from worknexus.modules.work_items.models import WorkItem


def require_work_item_permission(
    action: Permission,
) -> Callable[..., Coroutine[Any, Any, Subject]]:
    """Dependency factory for flat /work-items/{work_item_id} endpoints.

    Project-level members carry no tenant role, so a tenant-scope check would 403 them.
    This resolves the item's project_id first, then runs the project-scoped permission
    check (404 on missing/cross-tenant/soft-deleted)."""

    async def dependency(
        work_item_id: str,
        db: Annotated[AsyncSession, Depends(get_db)],
        subject: Annotated[Subject, Depends(get_current_subject)],
    ) -> Subject:
        item = await db.get(WorkItem, work_item_id)
        if item is None or item.tenant_id != subject.actor.tenant_id or item.deleted_at is not None:
            raise BizError(ErrorCode.WORK_ITEM_NOT_FOUND, "work item not found")
        scope = Scope(type=ScopeType.PROJECT, project_id=item.project_id)
        if not can(subject, action, scope):
            raise BizError(ErrorCode.FORBIDDEN, "permission denied")
        return subject

    return dependency
