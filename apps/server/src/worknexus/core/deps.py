from enum import StrEnum
from typing import Annotated

from fastapi import Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.config import get_settings
from worknexus.core.errors import BizError, ErrorCode
from worknexus.db import get_db


class ActorType(StrEnum):
    USER = "user"
    AI_AGENT = "ai_agent"
    SYSTEM = "system"


class Actor(BaseModel):
    id: str
    type: ActorType
    tenant_id: str


def system_actor(tenant_id: str) -> Actor:
    return Actor(id="system", type=ActorType.SYSTEM, tenant_id=tenant_id)


async def get_current_actor(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Actor:
    token = request.cookies.get(get_settings().session_cookie_name)
    if not token:
        raise BizError(ErrorCode.UNAUTHORIZED, "not authenticated")
    # Imported lazily: core must stay importable without the identity module.
    from worknexus.modules.identity import service as identity_service

    return await identity_service.resolve_session_actor(db, token)
