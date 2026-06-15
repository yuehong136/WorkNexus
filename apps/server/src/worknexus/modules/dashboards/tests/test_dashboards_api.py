"""dashboards REST: envelope smoke for the four endpoints + permission/not-found gating."""

from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.modules.identity.models import ProjectMember, User

pytestmark = pytest.mark.integration

API = "/api/v1"


@pytest.mark.p0
async def test_owner_reads_all_four_endpoints(owner_client: AsyncClient, initialized: SimpleNamespace) -> None:
    pid = initialized.project.id
    await owner_client.post(f"{API}/projects/{pid}/work-items", json={"type": "task", "title": "x"})

    summary = (await owner_client.get(f"{API}/projects/{pid}/dashboard/summary")).json()
    assert summary["code"] == 0
    assert summary["data"]["totalCount"] == 1
    assert "statusCounts" in summary["data"]
    assert len(summary["data"]["createdTrend"]) == 7

    workload = (await owner_client.get(f"{API}/projects/{pid}/dashboard/workload")).json()
    assert workload["code"] == 0
    assert "items" in workload["data"]

    overdue = (await owner_client.get(f"{API}/projects/{pid}/dashboard/overdue")).json()
    assert overdue["code"] == 0
    assert "pageSize" in overdue["data"]

    insights = (await owner_client.get(f"{API}/projects/{pid}/dashboard/ai-insights")).json()
    assert insights["code"] == 0
    assert insights["data"]["provenance"]["provider"] == "rules"


@pytest.mark.p1
async def test_unauthenticated_is_401(client: AsyncClient, initialized: SimpleNamespace) -> None:
    resp = await client.get(f"{API}/projects/{initialized.project.id}/dashboard/summary")
    assert resp.status_code == 401


@pytest.mark.p1
async def test_unknown_project_is_5002(owner_client: AsyncClient, initialized: SimpleNamespace) -> None:
    body = (await owner_client.get(f"{API}/projects/nope/dashboard/summary")).json()
    assert body["code"] == 5002


@pytest.mark.p1
async def test_non_member_forbidden(
    client: AsyncClient, initialized: SimpleNamespace, db: AsyncSession, member_user: User
) -> None:
    # member_user has no project membership / tenant role -> no dashboard.read on this project
    login = await client.post(f"{API}/auth/login", json={"email": "member@example.com", "password": "member-pass-123"})
    assert login.json()["code"] == 0
    resp = await client.get(f"{API}/projects/{initialized.project.id}/dashboard/summary")
    assert resp.status_code == 403


@pytest.mark.p1
async def test_viewer_can_read(
    client: AsyncClient, initialized: SimpleNamespace, db: AsyncSession, member_user: User
) -> None:
    db.add(
        ProjectMember(
            tenant_id=initialized.tenant.id,
            project_id=initialized.project.id,
            user_id=member_user.id,
            role="viewer",
            created_by=initialized.owner.id,
        )
    )
    await db.flush()
    login = await client.post(f"{API}/auth/login", json={"email": "member@example.com", "password": "member-pass-123"})
    assert login.json()["code"] == 0
    resp = (await client.get(f"{API}/projects/{initialized.project.id}/dashboard/summary")).json()
    assert resp["code"] == 0
