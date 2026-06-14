"""REST API tests for the read-only skills endpoints."""

from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.deps import Actor, ActorType
from worknexus.core.errors import ErrorCode
from worknexus.modules.identity.schemas import DelegationContext
from worknexus.modules.skills import service
from worknexus.modules.skills.schemas import RiskLevel, SkillInvocationStatus

pytestmark = pytest.mark.p1


async def _seed_invocation(db: AsyncSession, initialized: SimpleNamespace) -> str:
    actor = Actor(id=initialized.agent.id, type=ActorType.AI_AGENT, tenant_id=initialized.tenant.id)
    delegation = DelegationContext(
        tenant_id=initialized.tenant.id,
        user_id=initialized.owner.id,
        agent_id=initialized.agent.id,
        project_id=initialized.project.id,
        conversation_id=None,
        run_id=None,
        permissions_snapshot={"effective": ["work_item.read"]},
    )
    inv = await service.begin_invocation(
        db,
        actor,
        delegation=delegation,
        tool_name="workitem_get_work_item",
        risk_level=RiskLevel.READ,
        requires_confirmation=False,
        input_summary="{}",
    )
    await service.finish_invocation(db, inv, status=SkillInvocationStatus.SUCCESS, output_summary="{}")
    return inv.id


async def test_list_skills_endpoint(owner_client: AsyncClient) -> None:
    resp = await owner_client.get("/api/v1/skills")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    codes = {s["skillCode"] for s in body["data"]}
    assert "workitem-skill" in codes


async def test_list_invocations_endpoint(
    owner_client: AsyncClient, db: AsyncSession, initialized: SimpleNamespace
) -> None:
    await _seed_invocation(db, initialized)
    resp = await owner_client.get("/api/v1/skills/invocations")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["toolName"] == "workitem_get_work_item"
    assert body["data"]["items"][0]["representedUser"]["displayName"] == initialized.owner.display_name


async def test_get_invocation_endpoint(
    owner_client: AsyncClient, db: AsyncSession, initialized: SimpleNamespace
) -> None:
    invocation_id = await _seed_invocation(db, initialized)
    resp = await owner_client.get(f"/api/v1/skills/invocations/{invocation_id}")
    assert resp.json()["code"] == 0
    assert resp.json()["data"]["id"] == invocation_id

    missing = await owner_client.get("/api/v1/skills/invocations/nope")
    assert missing.json()["code"] == ErrorCode.SKILL_INVOCATION_NOT_FOUND


async def test_skills_requires_auth(client: AsyncClient, initialized: SimpleNamespace) -> None:
    resp = await client.get("/api/v1/skills")
    assert resp.status_code == 401
