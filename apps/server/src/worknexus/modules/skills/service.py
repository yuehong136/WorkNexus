from datetime import UTC, datetime

from fastmcp import FastMCP
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.deps import Actor
from worknexus.core.errors import BizError, ErrorCode
from worknexus.core.pagination import PageParams
from worknexus.modules.audit import service as audit
from worknexus.modules.audit.service import AuditAction
from worknexus.modules.identity.models import User
from worknexus.modules.identity.schemas import DelegationContext
from worknexus.modules.skills.models import SkillInvocation
from worknexus.modules.skills.reflection import (
    permission_for_tags,
    risk_for_tags,
    skill_code_for_tool,
)
from worknexus.modules.skills.schemas import (
    RepresentedUserOut,
    RiskLevel,
    SkillInvocationOut,
    SkillInvocationStatus,
    SkillOut,
    SkillToolOut,
)


def _now() -> datetime:
    return datetime.now(UTC)


async def begin_invocation(
    db: AsyncSession,
    actor: Actor,
    *,
    delegation: DelegationContext,
    tool_name: str,
    risk_level: RiskLevel,
    requires_confirmation: bool,
    input_summary: str,
) -> SkillInvocation:
    """Open a forensic record (status=running) + paired skill.invoke audit row.

    Written in the middleware's independent `log_db` so it survives even when the
    business transaction rolls back. Never commits — the caller owns the commit."""
    inv = SkillInvocation(
        tenant_id=actor.tenant_id,
        skill_code=skill_code_for_tool(tool_name),
        tool_name=tool_name,
        caller_type=actor.type,
        caller_id=actor.id,
        represented_user_id=delegation.user_id,
        agent_id=delegation.agent_id,
        project_id=delegation.project_id,
        conversation_id=delegation.conversation_id,
        run_id=delegation.run_id,
        input_summary=input_summary,
        status=SkillInvocationStatus.RUNNING,
        risk_level=risk_level,
        requires_confirmation=requires_confirmation,
        started_at=_now(),
    )
    db.add(inv)
    await db.flush()
    log = await audit.record(
        db,
        actor,
        action=AuditAction.SKILL_INVOKE,
        resource_type="skill_invocation",
        resource_id=inv.id,
        project_id=delegation.project_id,
        detail={"tool": tool_name, "risk": risk_level.value},
    )
    inv.audit_log_id = log.id
    await db.flush()
    return inv


async def finish_invocation(
    db: AsyncSession,
    inv: SkillInvocation,
    *,
    status: SkillInvocationStatus,
    output_summary: str | None = None,
    error_message: str | None = None,
) -> None:
    inv.status = status
    inv.output_summary = output_summary
    inv.error_message = error_message
    inv.finished_at = _now()
    await db.flush()


def _to_out(inv: SkillInvocation, users: dict[str, User]) -> SkillInvocationOut:
    out = SkillInvocationOut.model_validate(inv)
    user = users.get(inv.represented_user_id)
    if user is not None:
        out.represented_user = RepresentedUserOut(id=user.id, display_name=user.display_name)
    return out


async def _load_users(db: AsyncSession, invocations: list[SkillInvocation]) -> dict[str, User]:
    ids = {inv.represented_user_id for inv in invocations}
    if not ids:
        return {}
    rows = (await db.execute(select(User).where(User.id.in_(ids)))).scalars().all()
    return {u.id: u for u in rows}


async def list_invocations(
    db: AsyncSession,
    actor: Actor,
    *,
    params: PageParams,
    status: SkillInvocationStatus | None = None,
    risk_level: RiskLevel | None = None,
    tool_name: str | None = None,
) -> tuple[list[SkillInvocationOut], int]:
    base = select(SkillInvocation).where(SkillInvocation.tenant_id == actor.tenant_id)
    if status is not None:
        base = base.where(SkillInvocation.status == status)
    if risk_level is not None:
        base = base.where(SkillInvocation.risk_level == risk_level)
    if tool_name is not None:
        base = base.where(SkillInvocation.tool_name == tool_name)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    invocations = list(
        (
            await db.execute(
                base.order_by(SkillInvocation.created_at.desc()).offset(params.offset).limit(params.page_size)
            )
        )
        .scalars()
        .all()
    )
    users = await _load_users(db, invocations)
    return [_to_out(inv, users) for inv in invocations], total


async def get_invocation(db: AsyncSession, actor: Actor, invocation_id: str) -> SkillInvocationOut:
    inv = await db.get(SkillInvocation, invocation_id)
    if inv is None or inv.tenant_id != actor.tenant_id:
        raise BizError(ErrorCode.SKILL_INVOCATION_NOT_FOUND, "skill invocation not found")
    users = await _load_users(db, [inv])
    return _to_out(inv, users)


async def list_skills(mcp: FastMCP) -> list[SkillOut]:
    """Reflect the composed MCP server: namespace → skill, tags → risk / permission."""
    tools = await mcp.list_tools()
    groups: dict[str, list[SkillToolOut]] = {}
    for tool in tools:
        tags: set[str] = set(tool.tags or [])
        risk = risk_for_tags(tags)
        groups.setdefault(skill_code_for_tool(tool.name), []).append(
            SkillToolOut(
                tool_name=tool.name,
                risk_level=risk,
                executable_in_v01=risk == RiskLevel.READ,
                required_permission=permission_for_tags(tags),
            )
        )
    return [
        SkillOut(skill_code=code, tools=sorted(tools_, key=lambda t: t.tool_name))
        for code, tools_ in sorted(groups.items())
    ]
