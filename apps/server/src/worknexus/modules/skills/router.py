from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.access import Permission, Subject, require_permission
from worknexus.core.envelope import Envelope
from worknexus.core.pagination import Page, PageParamsDep
from worknexus.db import get_db
from worknexus.mcp import mcp
from worknexus.modules.skills import service
from worknexus.modules.skills.schemas import (
    RiskLevel,
    SkillInvocationOut,
    SkillInvocationStatus,
    SkillOut,
)

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", operation_id="list_skills")
async def list_skills(
    _: Annotated[Subject, Depends(require_permission(Permission.SKILL_READ))],
) -> Envelope[list[SkillOut]]:
    return Envelope(data=await service.list_skills(mcp))


@router.get("/invocations", operation_id="list_skill_invocations")
async def list_skill_invocations(
    db: Annotated[AsyncSession, Depends(get_db)],
    params: PageParamsDep,
    subject: Annotated[Subject, Depends(require_permission(Permission.SKILL_READ))],
    status: SkillInvocationStatus | None = None,
    risk_level: RiskLevel | None = None,
    tool_name: str | None = None,
) -> Envelope[Page[SkillInvocationOut]]:
    items, total = await service.list_invocations(
        db, subject.actor, params=params, status=status, risk_level=risk_level, tool_name=tool_name
    )
    return Envelope(data=Page.build(items, total, params))


@router.get("/invocations/{invocation_id}", operation_id="get_skill_invocation")
async def get_skill_invocation(
    invocation_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: Annotated[Subject, Depends(require_permission(Permission.SKILL_READ))],
) -> Envelope[SkillInvocationOut]:
    return Envelope(data=await service.get_invocation(db, subject.actor, invocation_id))
