"""audit REST: tenant-level audit.read gate (owner only; project roles do NOT grant it)
+ envelope/filter smoke."""

from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.modules.identity.models import ProjectMember, User

pytestmark = pytest.mark.integration

API = "/api/v1"


@pytest.mark.p0
async def test_owner_reads_audit_logs(owner_client: AsyncClient, initialized: SimpleNamespace) -> None:
    pid = initialized.project.id
    await owner_client.post(f"{API}/projects/{pid}/work-items", json={"type": "task", "title": "x"})

    body = (await owner_client.get(f"{API}/audit-logs")).json()
    assert body["code"] == 0
    assert body["data"]["total"] >= 1
    assert "pageSize" in body["data"]
    actions = {row["action"] for row in body["data"]["items"]}
    assert "work_item.create" in actions
    row = next(r for r in body["data"]["items"] if r["action"] == "work_item.create")
    assert row["actor"]["type"] == "user"
    assert row["actor"]["displayName"] == "Owner"


@pytest.mark.p1
async def test_filter_by_action(owner_client: AsyncClient, initialized: SimpleNamespace) -> None:
    pid = initialized.project.id
    await owner_client.post(f"{API}/projects/{pid}/work-items", json={"type": "task", "title": "x"})

    body = (await owner_client.get(f"{API}/audit-logs", params={"action": "work_item.create"})).json()
    assert body["code"] == 0
    assert body["data"]["total"] >= 1
    assert all(r["action"] == "work_item.create" for r in body["data"]["items"])


@pytest.mark.p1
async def test_unauthenticated_is_401(client: AsyncClient, initialized: SimpleNamespace) -> None:
    assert (await client.get(f"{API}/audit-logs")).status_code == 401


@pytest.mark.p1
async def test_member_forbidden(client: AsyncClient, initialized: SimpleNamespace, member_user: User) -> None:
    login = await client.post(f"{API}/auth/login", json={"email": "member@example.com", "password": "member-pass-123"})
    assert login.json()["code"] == 0
    assert (await client.get(f"{API}/audit-logs")).status_code == 403


@pytest.mark.p1
async def test_project_admin_still_forbidden(
    client: AsyncClient, initialized: SimpleNamespace, db: AsyncSession, member_user: User
) -> None:
    # audit.read is tenant-level (owner/admin); a project_admin role must NOT grant it.
    db.add(
        ProjectMember(
            tenant_id=initialized.tenant.id,
            project_id=initialized.project.id,
            user_id=member_user.id,
            role="project_admin",
            created_by=initialized.owner.id,
        )
    )
    await db.flush()
    login = await client.post(f"{API}/auth/login", json={"email": "member@example.com", "password": "member-pass-123"})
    assert login.json()["code"] == 0
    assert (await client.get(f"{API}/audit-logs")).status_code == 403
