"""REST-level projects tests: CRUD, archive, visibility filtering and member management."""

from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.modules.audit.models import AuditLog
from worknexus.modules.identity import service as identity_service
from worknexus.modules.identity.models import ProjectMember, User

MEMBER_PASSWORD = "member-pass-123"


async def _login(client: AsyncClient, email: str, password: str = MEMBER_PASSWORD) -> None:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.json()["code"] == 0, resp.json()


async def _make_user(
    db: AsyncSession,
    initialized: SimpleNamespace,
    email: str,
    *,
    role: str | None = None,
    project_id: str | None = None,
) -> User:
    user = User(
        tenant_id=initialized.tenant.id,
        email=email,
        display_name=email.split("@")[0],
        password_hash=await identity_service.hash_password(MEMBER_PASSWORD),
        status="active",
    )
    db.add(user)
    await db.flush()
    if role is not None and project_id is not None:
        db.add(
            ProjectMember(
                tenant_id=initialized.tenant.id,
                project_id=project_id,
                user_id=user.id,
                role=role,
                created_by=initialized.owner.id,
            )
        )
        await db.flush()
    return user


async def _create_project(owner_client: AsyncClient, *, name: str, key: str, description: str | None = None) -> dict:
    body: dict[str, object] = {"name": name, "key": key}
    if description is not None:
        body["description"] = description
    resp = await owner_client.post("/api/v1/projects", json=body)
    data = resp.json()
    assert data["code"] == 0, data
    return data["data"]


@pytest.mark.p0
async def test_list_projects_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/projects")
    assert resp.status_code == 401


@pytest.mark.p0
async def test_owner_creates_and_lists_project(owner_client: AsyncClient, initialized: SimpleNamespace) -> None:
    created = await _create_project(owner_client, name="Beta", key="beta", description="hi")
    assert created["key"] == "BETA"  # normalized to uppercase
    assert created["status"] == "active"
    assert created["ownerId"] == initialized.owner.id
    assert created["owner"]["email"] == "owner@example.com"
    assert created["memberCount"] == 0
    assert "member_count" not in created  # Envelope payload is camelCase only

    page = (await owner_client.get("/api/v1/projects")).json()["data"]
    assert {p["key"] for p in page["items"]} >= {"WNX", "BETA"}
    assert page["total"] >= 2


@pytest.mark.p0
async def test_create_project_rejects_duplicate_key(owner_client: AsyncClient) -> None:
    await _create_project(owner_client, name="Gamma", key="GAM")
    resp = await owner_client.post("/api/v1/projects", json={"name": "Gamma 2", "key": "GAM"})
    assert resp.status_code == 200
    assert resp.json()["code"] == 5001


@pytest.mark.p1
async def test_list_matches_me_for_owner(owner_client: AsyncClient) -> None:
    await _create_project(owner_client, name="Beta", key="BETA")
    me = (await owner_client.get("/api/v1/me")).json()["data"]
    listed = (await owner_client.get("/api/v1/projects")).json()["data"]
    assert {p["id"] for p in me["projects"]} == {p["id"] for p in listed["items"]}


@pytest.mark.p1
async def test_member_sees_only_their_projects(
    owner_client: AsyncClient, client: AsyncClient, db: AsyncSession, initialized: SimpleNamespace
) -> None:
    await _create_project(owner_client, name="Beta", key="BETA")  # not visible to the viewer
    await _make_user(db, initialized, "viewer@example.com", role="viewer", project_id=initialized.project.id)
    await _login(client, "viewer@example.com")

    listed = (await client.get("/api/v1/projects")).json()["data"]
    assert {p["key"] for p in listed["items"]} == {"WNX"}
    me = (await client.get("/api/v1/me")).json()["data"]
    assert {p["id"] for p in me["projects"]} == {p["id"] for p in listed["items"]}


@pytest.mark.p1
async def test_archive_hides_from_default_list(owner_client: AsyncClient) -> None:
    beta = await _create_project(owner_client, name="Beta", key="BETA")
    resp = await owner_client.post(f"/api/v1/projects/{beta['id']}/archive")
    assert resp.json()["data"]["status"] == "archived"

    active = (await owner_client.get("/api/v1/projects")).json()["data"]
    assert beta["id"] not in {p["id"] for p in active["items"]}
    archived = (await owner_client.get("/api/v1/projects?status=archived")).json()["data"]
    assert beta["id"] in {p["id"] for p in archived["items"]}


@pytest.mark.p1
async def test_get_unknown_project_returns_5002(owner_client: AsyncClient) -> None:
    resp = await owner_client.get("/api/v1/projects/does-not-exist")
    assert resp.json()["code"] == 5002


@pytest.mark.p1
async def test_project_admin_can_update_and_archive(
    owner_client: AsyncClient, client: AsyncClient, db: AsyncSession, initialized: SimpleNamespace
) -> None:
    beta = await _create_project(owner_client, name="Beta", key="BETA")
    await _make_user(db, initialized, "padmin@example.com", role="project_admin", project_id=beta["id"])
    await _login(client, "padmin@example.com")

    resp = await client.patch(f"/api/v1/projects/{beta['id']}", json={"name": "Beta Prime"})
    assert resp.json()["code"] == 0
    assert resp.json()["data"]["name"] == "Beta Prime"
    resp = await client.post(f"/api/v1/projects/{beta['id']}/archive")
    assert resp.json()["data"]["status"] == "archived"


@pytest.mark.p1
async def test_member_cannot_update_project(
    client: AsyncClient, db: AsyncSession, initialized: SimpleNamespace
) -> None:
    await _make_user(db, initialized, "mem@example.com", role="member", project_id=initialized.project.id)
    await _login(client, "mem@example.com")
    resp = await client.patch(f"/api/v1/projects/{initialized.project.id}", json={"name": "Hacked"})
    assert resp.status_code == 403


@pytest.mark.p1
async def test_viewer_cannot_manage_members(
    client: AsyncClient, db: AsyncSession, initialized: SimpleNamespace
) -> None:
    target = await _make_user(db, initialized, "target@example.com")
    await _make_user(db, initialized, "viewer@example.com", role="viewer", project_id=initialized.project.id)
    await _login(client, "viewer@example.com")
    resp = await client.post(
        f"/api/v1/projects/{initialized.project.id}/members", json={"userId": target.id, "role": "member"}
    )
    assert resp.status_code == 403


@pytest.mark.p1
async def test_member_management_lifecycle_and_audit(
    owner_client: AsyncClient, db: AsyncSession, initialized: SimpleNamespace
) -> None:
    alice = await _make_user(db, initialized, "alice@example.com")
    pid = initialized.project.id

    resp = await owner_client.post(f"/api/v1/projects/{pid}/members", json={"userId": alice.id, "role": "member"})
    member = resp.json()["data"]
    assert member["userId"] == alice.id
    assert member["role"] == "member"
    assert member["email"] == "alice@example.com"

    members = (await owner_client.get(f"/api/v1/projects/{pid}/members")).json()["data"]
    assert any(m["userId"] == alice.id for m in members)

    resp = await owner_client.patch(f"/api/v1/projects/{pid}/members/{alice.id}", json={"role": "viewer"})
    assert resp.json()["data"]["role"] == "viewer"

    resp = await owner_client.delete(f"/api/v1/projects/{pid}/members/{alice.id}")
    assert resp.json()["code"] == 0
    members = (await owner_client.get(f"/api/v1/projects/{pid}/members")).json()["data"]
    assert all(m["userId"] != alice.id for m in members)

    actions = set((await db.execute(select(AuditLog.action))).scalars().all())
    assert {"project.member.add", "project.member.update", "project.member.remove"} <= actions


@pytest.mark.p1
async def test_project_changes_write_audit(
    owner_client: AsyncClient, db: AsyncSession, initialized: SimpleNamespace
) -> None:
    beta = await _create_project(owner_client, name="Beta", key="BETA")
    await owner_client.patch(f"/api/v1/projects/{beta['id']}", json={"description": "updated"})
    await owner_client.post(f"/api/v1/projects/{beta['id']}/archive")
    actions = set((await db.execute(select(AuditLog.action))).scalars().all())
    assert {"project.create", "project.update", "project.archive"} <= actions


@pytest.mark.p1
async def test_add_duplicate_member_returns_5003(
    owner_client: AsyncClient, db: AsyncSession, initialized: SimpleNamespace
) -> None:
    alice = await _make_user(db, initialized, "alice@example.com")
    pid = initialized.project.id
    await owner_client.post(f"/api/v1/projects/{pid}/members", json={"userId": alice.id, "role": "member"})
    resp = await owner_client.post(f"/api/v1/projects/{pid}/members", json={"userId": alice.id, "role": "member"})
    assert resp.json()["code"] == 5003


@pytest.mark.p1
async def test_manage_non_member_returns_5004(
    owner_client: AsyncClient, db: AsyncSession, initialized: SimpleNamespace
) -> None:
    bob = await _make_user(db, initialized, "bob@example.com")
    pid = initialized.project.id
    resp = await owner_client.patch(f"/api/v1/projects/{pid}/members/{bob.id}", json={"role": "viewer"})
    assert resp.json()["code"] == 5004
    resp = await owner_client.delete(f"/api/v1/projects/{pid}/members/{bob.id}")
    assert resp.json()["code"] == 5004


@pytest.mark.p1
async def test_cannot_manage_owner_membership_returns_5005(
    owner_client: AsyncClient, initialized: SimpleNamespace
) -> None:
    resp = await owner_client.post(
        f"/api/v1/projects/{initialized.project.id}/members",
        json={"userId": initialized.owner.id, "role": "member"},
    )
    assert resp.json()["code"] == 5005
