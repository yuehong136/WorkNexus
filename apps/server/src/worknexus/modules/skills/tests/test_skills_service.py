"""Service-layer tests: invocation write/read + reflective list_skills (real PG)."""

from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.deps import Actor, ActorType
from worknexus.core.errors import BizError, ErrorCode
from worknexus.core.pagination import PageParams
from worknexus.mcp import mcp
from worknexus.modules.identity.schemas import DelegationContext
from worknexus.modules.skills import service
from worknexus.modules.skills.models import SkillInvocation
from worknexus.modules.skills.schemas import RiskLevel, SkillInvocationStatus

pytestmark = pytest.mark.p1


def _actor(initialized: SimpleNamespace) -> Actor:
    return Actor(id=initialized.agent.id, type=ActorType.AI_AGENT, tenant_id=initialized.tenant.id)


def _delegation(initialized: SimpleNamespace) -> DelegationContext:
    return DelegationContext(
        tenant_id=initialized.tenant.id,
        user_id=initialized.owner.id,
        agent_id=initialized.agent.id,
        project_id=initialized.project.id,
        conversation_id="conv-1",
        run_id="run-1",
        permissions_snapshot={"effective": ["work_item.read"]},
    )


async def _seed(
    db: AsyncSession, initialized: SimpleNamespace, *, tool_name: str, status: SkillInvocationStatus
) -> SkillInvocation:
    inv = await service.begin_invocation(
        db,
        _actor(initialized),
        delegation=_delegation(initialized),
        tool_name=tool_name,
        risk_level=RiskLevel.READ,
        requires_confirmation=False,
        input_summary="{}",
    )
    await service.finish_invocation(db, inv, status=status, output_summary="{}")
    return inv


async def test_begin_invocation_links_audit_log(db: AsyncSession, initialized: SimpleNamespace) -> None:
    inv = await _seed(db, initialized, tool_name="workitem_get_work_item", status=SkillInvocationStatus.SUCCESS)
    assert inv.audit_log_id is not None
    assert inv.skill_code == "workitem-skill"
    assert inv.represented_user_id == initialized.owner.id
    assert inv.caller_id == initialized.agent.id
    assert inv.finished_at is not None


async def test_list_invocations_filters_and_represented_user(db: AsyncSession, initialized: SimpleNamespace) -> None:
    await _seed(db, initialized, tool_name="workitem_get_work_item", status=SkillInvocationStatus.SUCCESS)
    await _seed(db, initialized, tool_name="workitem_search_work_items", status=SkillInvocationStatus.FAILED)

    items, total = await service.list_invocations(db, _actor(initialized), params=PageParams())
    assert total == 2
    assert items[0].represented_user is not None
    assert items[0].represented_user.display_name == initialized.owner.display_name

    failed, total_failed = await service.list_invocations(
        db, _actor(initialized), params=PageParams(), status=SkillInvocationStatus.FAILED
    )
    assert total_failed == 1
    assert failed[0].tool_name == "workitem_search_work_items"


async def test_get_invocation_not_found(db: AsyncSession, initialized: SimpleNamespace) -> None:
    with pytest.raises(BizError) as exc:
        await service.get_invocation(db, _actor(initialized), "does-not-exist")
    assert exc.value.code == ErrorCode.SKILL_INVOCATION_NOT_FOUND


async def test_list_skills_reflects_composition() -> None:
    skills = {s.skill_code: s for s in await service.list_skills(mcp)}
    assert "workitem-skill" in skills
    assert "system-skill" in skills

    tools = {t.tool_name: t for t in skills["workitem-skill"].tools}
    assert tools["workitem_get_work_item"].risk_level == RiskLevel.READ
    assert tools["workitem_get_work_item"].executable_in_v01 is True
    assert tools["workitem_create_work_item"].risk_level == RiskLevel.LOW_WRITE
    assert tools["workitem_create_work_item"].executable_in_v01 is False
    assert tools["workitem_create_work_item"].required_permission is not None
