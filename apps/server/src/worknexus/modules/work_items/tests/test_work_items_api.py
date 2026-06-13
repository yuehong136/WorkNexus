"""Work-item REST + service tests against real PostgreSQL (rollback fixture)."""

from types import SimpleNamespace
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.deps import Actor, ActorType
from worknexus.modules.audit.models import AuditLog
from worknexus.modules.identity import service as identity_service
from worknexus.modules.identity.models import ProjectMember, User
from worknexus.modules.work_items import service
from worknexus.modules.work_items.models import WorkItemActivity
from worknexus.modules.work_items.schemas import WorkItemCreateIn, WorkItemSource, WorkItemType

pytestmark = pytest.mark.integration

API = "/api/v1"


def _owner_actor(initialized: SimpleNamespace) -> Actor:
    return Actor(id=initialized.owner.id, type=ActorType.USER, tenant_id=initialized.tenant.id)


async def _create(client: AsyncClient, project_id: str, **body: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"type": "task", "title": "Item", **body}
    resp = await client.post(f"{API}/projects/{project_id}/work-items", json=payload)
    body_json: dict[str, Any] = resp.json()
    return body_json


@pytest.mark.p0
async def test_create_assigns_sequential_keys(owner_client: AsyncClient, initialized: SimpleNamespace) -> None:
    pid = initialized.project.id
    first = await _create(owner_client, pid, type="bug", title="First", customFields={"severity": "high"})
    assert first["code"] == 0
    assert first["data"]["key"].endswith("-1")
    assert first["data"]["source"] == "manual"
    assert first["data"]["status"] == "backlog"
    assert first["data"]["customFields"] == {"severity": "high"}
    second = await _create(owner_client, pid, title="Second")
    assert second["data"]["key"].endswith("-2")


@pytest.mark.p1
async def test_invalid_custom_fields_rejected(owner_client: AsyncClient, initialized: SimpleNamespace) -> None:
    body = await _create(owner_client, initialized.project.id, type="bug", customFields={"unknown_key": "x"})
    assert body["code"] == 2007


@pytest.mark.p1
async def test_list_filters_by_type(owner_client: AsyncClient, initialized: SimpleNamespace) -> None:
    pid = initialized.project.id
    await _create(owner_client, pid, type="bug", title="b")
    await _create(owner_client, pid, type="task", title="t")
    listed = (await owner_client.get(f"{API}/projects/{pid}/work-items")).json()["data"]
    assert listed["total"] == 2
    assert "pageSize" in listed
    filtered = (await owner_client.get(f"{API}/projects/{pid}/work-items", params={"type": "bug"})).json()["data"]
    assert filtered["total"] == 1
    assert filtered["items"][0]["type"] == "bug"


@pytest.mark.p0
async def test_transition_valid_invalid_and_dual_log(
    owner_client: AsyncClient, initialized: SimpleNamespace, db: AsyncSession
) -> None:
    pid = initialized.project.id
    item_id = (await _create(owner_client, pid))["data"]["id"]
    ok = await owner_client.post(f"{API}/work-items/{item_id}/transition", json={"status": "todo"})
    assert ok.json()["data"]["status"] == "todo"
    bad = await owner_client.post(f"{API}/work-items/{item_id}/transition", json={"status": "done"})
    assert bad.json()["code"] == 2002
    activities = (
        (
            await db.execute(
                select(WorkItemActivity).where(
                    WorkItemActivity.work_item_id == item_id, WorkItemActivity.action == "status_changed"
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(activities) == 1
    audits = (
        (
            await db.execute(
                select(AuditLog).where(AuditLog.resource_id == item_id, AuditLog.action == "work_item.transition")
            )
        )
        .scalars()
        .all()
    )
    assert len(audits) == 1


@pytest.mark.p1
async def test_soft_delete_hides_item(owner_client: AsyncClient, initialized: SimpleNamespace) -> None:
    pid = initialized.project.id
    item_id = (await _create(owner_client, pid))["data"]["id"]
    assert (await owner_client.delete(f"{API}/work-items/{item_id}")).json()["code"] == 0
    assert (await owner_client.get(f"{API}/work-items/{item_id}")).json()["code"] == 2001
    assert (await owner_client.get(f"{API}/projects/{pid}/work-items")).json()["data"]["total"] == 0


@pytest.mark.p1
async def test_assignee_validation(owner_client: AsyncClient, initialized: SimpleNamespace, member_user: User) -> None:
    pid = initialized.project.id
    rejected = await _create(owner_client, pid, assigneeId=member_user.id)
    assert rejected["code"] == 2008
    accepted = await _create(owner_client, pid, assigneeId=initialized.owner.id)
    assert accepted["data"]["assigneeId"] == initialized.owner.id


@pytest.mark.p1
async def test_archived_project_blocks_create(owner_client: AsyncClient, initialized: SimpleNamespace) -> None:
    pid = initialized.project.id
    assert (await owner_client.post(f"{API}/projects/{pid}/archive")).json()["code"] == 0
    assert (await _create(owner_client, pid))["code"] == 2009


@pytest.mark.p1
async def test_viewer_cannot_create(client: AsyncClient, initialized: SimpleNamespace, db: AsyncSession) -> None:
    pid = initialized.project.id
    tenant_id = initialized.tenant.id
    viewer = User(
        tenant_id=tenant_id,
        email="viewer@example.com",
        display_name="Viewer",
        password_hash=await identity_service.hash_password("viewer-pass-123"),
        status="active",
    )
    db.add(viewer)
    await db.flush()
    db.add(
        ProjectMember(
            tenant_id=tenant_id, project_id=pid, user_id=viewer.id, role="viewer", created_by=initialized.owner.id
        )
    )
    await db.flush()
    login = await client.post(f"{API}/auth/login", json={"email": "viewer@example.com", "password": "viewer-pass-123"})
    assert login.json()["code"] == 0
    resp = await client.post(f"{API}/projects/{pid}/work-items", json={"type": "task", "title": "x"})
    assert resp.status_code == 403


@pytest.mark.p1
async def test_non_member_cannot_read_flat_item(
    client: AsyncClient, initialized: SimpleNamespace, db: AsyncSession, member_user: User
) -> None:
    pid = initialized.project.id
    created = await service.create_work_item(
        db, _owner_actor(initialized), pid, WorkItemCreateIn(type=WorkItemType.TASK, title="x")
    )
    login = await client.post(f"{API}/auth/login", json={"email": "member@example.com", "password": "member-pass-123"})
    assert login.json()["code"] == 0
    resp = await client.get(f"{API}/work-items/{created.id}")
    assert resp.status_code == 403


@pytest.mark.p1
async def test_project_summary(owner_client: AsyncClient, initialized: SimpleNamespace, db: AsyncSession) -> None:
    pid = initialized.project.id
    await _create(owner_client, pid, priority="high")
    # AI-created item (source=mcp) via the service so aiCreatedCount is exercised.
    await service.create_work_item(
        db,
        _owner_actor(initialized),
        pid,
        WorkItemCreateIn(type=WorkItemType.TASK, title="ai"),
        source=WorkItemSource.MCP,
    )
    summary = (await owner_client.get(f"{API}/projects/{pid}/summary")).json()["data"]
    assert summary["totalCount"] == 2
    assert summary["highPriorityCount"] == 1
    assert summary["aiCreatedCount"] == 1
    assert summary["statusCounts"]["backlog"] == 2
    assert len(summary["recentActivities"]) >= 1
