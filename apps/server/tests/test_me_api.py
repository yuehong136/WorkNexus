"""GET /me and GET /users with permission enforcement."""

from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.modules.identity.models import ProjectMember, User

pytestmark = pytest.mark.integration


@pytest.mark.p0
async def test_me_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/me")
    assert resp.status_code == 401


@pytest.mark.p0
async def test_me_owner_context(owner_client: AsyncClient, initialized: SimpleNamespace) -> None:
    resp = await owner_client.get("/api/v1/me")
    ctx = resp.json()["data"]
    assert ctx["user"]["id"] == initialized.owner.id
    assert ctx["roles"] == ["owner"]
    assert "user.invite" in ctx["permissions"]
    assert ctx["projects"][0]["role"] == "owner"
    assert ctx["ai"]["availableAgents"][0]["id"] == initialized.agent.id


@pytest.mark.p1
async def test_me_project_member_context(
    client: AsyncClient, db: AsyncSession, initialized: SimpleNamespace, member_user: User
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
    resp = await client.post("/api/v1/auth/login", json={"email": "member@example.com", "password": "member-pass-123"})
    assert resp.json()["code"] == 0
    resp = await client.get("/api/v1/me")
    ctx = resp.json()["data"]
    assert ctx["roles"] == []
    assert "user.read" in ctx["permissions"]
    assert "user.invite" not in ctx["permissions"]
    assert [p["role"] for p in ctx["projects"]] == ["viewer"]
    assert "work_item.create" not in ctx["projects"][0]["permissions"]


@pytest.mark.p1
async def test_users_list_pagination_and_permission(
    owner_client: AsyncClient, member_user: User, initialized: SimpleNamespace
) -> None:
    resp = await owner_client.get("/api/v1/users", params={"page": 1, "page_size": 10})
    data = resp.json()["data"]
    assert data["total"] == 2
    emails = {u["email"] for u in data["items"]}
    assert emails == {"owner@example.com", "member@example.com"}
    assert {"status", "lastLoginAt", "createdAt"} <= set(data["items"][0])


@pytest.mark.p1
async def test_users_list_requires_permission(client: AsyncClient, member_user: User) -> None:
    # member_user has no project membership and no tenant role -> no user.read.
    resp = await client.post("/api/v1/auth/login", json={"email": "member@example.com", "password": "member-pass-123"})
    assert resp.json()["code"] == 0
    resp = await client.get("/api/v1/users")
    assert resp.status_code == 403
