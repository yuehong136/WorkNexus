from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.access import Permission, Scope, ScopeType, Subject, can, get_current_subject
from worknexus.core.errors import BizError, ErrorCode
from worknexus.db import get_db
from worknexus.modules.intake.models import IntakeRequest


def require_intake_permission(
    action: Permission,
) -> Callable[..., Coroutine[Any, Any, Subject]]:
    """Dependency factory for flat /intake/{intake_id} endpoints: resolve the row's project
    first, then run the project-scoped permission check (404 on missing/cross-tenant/deleted)."""

    async def dependency(
        intake_id: str,
        db: Annotated[AsyncSession, Depends(get_db)],
        subject: Annotated[Subject, Depends(get_current_subject)],
    ) -> Subject:
        row = await db.get(IntakeRequest, intake_id)
        if row is None or row.tenant_id != subject.actor.tenant_id or row.deleted_at is not None:
            raise BizError(ErrorCode.INTAKE_NOT_FOUND, "intake request not found")
        scope = Scope(type=ScopeType.PROJECT, project_id=row.project_id)
        if not can(subject, action, scope):
            raise BizError(ErrorCode.FORBIDDEN, "permission denied")
        return subject

    return dependency
