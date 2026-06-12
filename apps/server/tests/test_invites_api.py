"""Invite lifecycle through the REST API: create / list / preview / accept / revoke."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.modules.audit.models import AuditLog
from worknexus.modules.identity.models import InviteToken, ProjectMember, RoleBinding

pytestmark = pytest.mark.integration


async def _create_invite(owner_client: AsyncClient, payload: dict[str, Any]) -> dict[str, Any]:
    resp = await owner_client.post("/api/v1/invites", json=payload)
    body = resp.json()
    assert body["code"] == 0, body
    data: dict[str, Any] = body["data"]
    return data


@pytest.mark.p0
async def test_project_invite_full_lifecycle(
    owner_client: AsyncClient, db: AsyncSession, initialized: SimpleNamespace
) -> None:
    created = await _create_invite(
        owner_client,
        {"email": "invitee@example.com", "projectId": initialized.project.id, "projectRole": "member"},
    )
    token = created["token"]
    assert token.startswith("wn_inv_")
    assert created["invite"]["status"] == "pending"

    # Public preview shows the target without authentication.
    resp = await owner_client.get(f"/api/v1/invites/{token}")
    preview = resp.json()["data"]
    assert preview["email"] == "invitee@example.com"
    assert preview["projectName"] == "WorkNexus Internal"
    assert preview["projectRole"] == "member"

    resp = await owner_client.post(
        f"/api/v1/invites/{token}/accept",
        json={"displayName": "Invitee", "password": "invitee-pass-123"},
    )
    body = resp.json()
    assert body["code"] == 0
    ctx = body["data"]
    assert ctx["user"]["email"] == "invitee@example.com"
    assert ctx["roles"] == []
    assert [p["role"] for p in ctx["projects"]] == ["member"]

    member = (await db.execute(select(ProjectMember).where(ProjectMember.role == "member"))).scalar_one()
    assert member.project_id == initialized.project.id

    actions = set((await db.execute(select(AuditLog.action))).scalars().all())
    assert {"invite.create", "invite.accept", "project.member.add"} <= actions


@pytest.mark.p1
async def test_tenant_admin_invite_writes_role_binding_not_membership(
    owner_client: AsyncClient, db: AsyncSession, initialized: SimpleNamespace
) -> None:
    created = await _create_invite(owner_client, {"email": "admin2@example.com", "tenantRole": "admin"})
    resp = await owner_client.post(
        f"/api/v1/invites/{created['token']}/accept",
        json={"displayName": "Admin Two", "password": "admin2-pass-123"},
    )
    ctx = resp.json()["data"]
    assert ctx["roles"] == ["admin"]
    assert "user.invite" in ctx["permissions"]

    binding = (await db.execute(select(RoleBinding).where(RoleBinding.role == "admin"))).scalar_one()
    assert binding.subject_type == "user"
    memberships = (await db.execute(select(ProjectMember))).scalars().all()
    assert memberships == []  # D3: tenant role must not be mirrored into project_members


@pytest.mark.p0
async def test_member_cannot_create_invites(
    owner_client: AsyncClient, client: AsyncClient, initialized: SimpleNamespace
) -> None:
    created = await _create_invite(
        owner_client,
        {"email": "member2@example.com", "projectId": initialized.project.id, "projectRole": "member"},
    )
    await client.post(
        f"/api/v1/invites/{created['token']}/accept",
        json={"displayName": "Member Two", "password": "member2-pass-123"},
    )
    # client now authenticated as the project member via the accept auto-login.
    resp = await client.post(
        "/api/v1/invites",
        json={"email": "x@example.com", "projectId": initialized.project.id, "projectRole": "member"},
    )
    assert resp.status_code == 403
    resp = await client.get("/api/v1/invites")
    assert resp.status_code == 403


@pytest.mark.p1
async def test_invite_requires_auth(client: AsyncClient, initialized: SimpleNamespace) -> None:
    resp = await client.post("/api/v1/invites", json={"email": "a@b.com", "tenantRole": "admin"})
    assert resp.status_code == 401


@pytest.mark.p1
async def test_invite_target_xor_validation(owner_client: AsyncClient, initialized: SimpleNamespace) -> None:
    for payload in (
        {"email": "x@example.com"},
        {"email": "x@example.com", "tenantRole": "admin", "projectId": initialized.project.id},
        {"email": "x@example.com", "tenantRole": "owner"},
        {"email": "x@example.com", "projectId": initialized.project.id, "projectRole": "owner"},
    ):
        resp = await owner_client.post("/api/v1/invites", json=payload)
        assert resp.json()["code"] == 1002, payload


@pytest.mark.p1
async def test_invite_duplicate_email_rules(owner_client: AsyncClient, initialized: SimpleNamespace) -> None:
    resp = await owner_client.post("/api/v1/invites", json={"email": "owner@example.com", "tenantRole": "admin"})
    assert resp.json()["code"] == 4004  # existing user

    await _create_invite(owner_client, {"email": "dup@example.com", "tenantRole": "admin"})
    resp = await owner_client.post("/api/v1/invites", json={"email": "dup@example.com", "tenantRole": "admin"})
    assert resp.json()["code"] == 4004  # pending invite exists


@pytest.mark.p1
async def test_revoked_invite_cannot_be_accepted(owner_client: AsyncClient, initialized: SimpleNamespace) -> None:
    created = await _create_invite(owner_client, {"email": "rev@example.com", "tenantRole": "admin"})
    resp = await owner_client.post(f"/api/v1/invites/{created['invite']['id']}/revoke")
    assert resp.json()["data"]["status"] == "revoked"
    resp = await owner_client.post(
        f"/api/v1/invites/{created['token']}/accept",
        json={"displayName": "Rev", "password": "rev-pass-12345"},
    )
    assert resp.json()["code"] == 4008


@pytest.mark.p1
async def test_expired_invite_cannot_be_accepted(
    owner_client: AsyncClient, db: AsyncSession, initialized: SimpleNamespace
) -> None:
    created = await _create_invite(owner_client, {"email": "late@example.com", "tenantRole": "admin"})
    invite = await db.get(InviteToken, created["invite"]["id"])
    assert invite is not None
    invite.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db.flush()
    resp = await owner_client.get(f"/api/v1/invites/{created['token']}")
    assert resp.json()["data"]["status"] == "expired"
    resp = await owner_client.post(
        f"/api/v1/invites/{created['token']}/accept",
        json={"displayName": "Late", "password": "late-pass-12345"},
    )
    assert resp.json()["code"] == 4006


@pytest.mark.p1
async def test_invite_cannot_be_accepted_twice(owner_client: AsyncClient, initialized: SimpleNamespace) -> None:
    created = await _create_invite(owner_client, {"email": "twice@example.com", "tenantRole": "admin"})
    accept = {"displayName": "Twice", "password": "twice-pass-1234"}
    resp = await owner_client.post(f"/api/v1/invites/{created['token']}/accept", json=accept)
    assert resp.json()["code"] == 0
    resp = await owner_client.post(f"/api/v1/invites/{created['token']}/accept", json=accept)
    assert resp.json()["code"] == 4007


@pytest.mark.p1
async def test_accept_rejects_weak_password(owner_client: AsyncClient, initialized: SimpleNamespace) -> None:
    created = await _create_invite(owner_client, {"email": "weak@example.com", "tenantRole": "admin"})
    resp = await owner_client.post(
        f"/api/v1/invites/{created['token']}/accept", json={"displayName": "Weak", "password": "short"}
    )
    assert resp.json()["code"] == 4012


@pytest.mark.p1
async def test_unknown_invite_token(client: AsyncClient, initialized: SimpleNamespace) -> None:
    resp = await client.get("/api/v1/invites/wn_inv_does-not-exist")
    assert resp.json()["code"] == 4005


@pytest.mark.p2
async def test_invite_list_pagination_shape(owner_client: AsyncClient, initialized: SimpleNamespace) -> None:
    await _create_invite(owner_client, {"email": "l1@example.com", "tenantRole": "admin"})
    await _create_invite(owner_client, {"email": "l2@example.com", "tenantRole": "admin"})
    resp = await owner_client.get("/api/v1/invites", params={"page": 1, "page_size": 1})
    data = resp.json()["data"]
    assert data["total"] == 2
    assert data["page"] == 1
    assert data["pageSize"] == 1
    assert len(data["items"]) == 1
