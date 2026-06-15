"""intake REST surface over httpx ASGITransport: create (with triage), list, accept→
work item, reject, and 404 mapping."""

from types import SimpleNamespace
from typing import Any

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.p1


async def _create(client: AsyncClient, project_id: str, title: str = "Login crash") -> dict[str, Any]:
    resp = await client.post(
        f"/api/v1/projects/{project_id}/intake",
        json={"title": title, "description": "The app crashes on login, urgent"},
    )
    body = resp.json()
    assert body["code"] == 0, body
    result: dict[str, Any] = body["data"]
    return result


async def test_create_lists_and_carries_triage(owner_client: AsyncClient, initialized: SimpleNamespace) -> None:
    project_id = initialized.project.id
    created = await _create(owner_client, project_id)
    assert created["status"] == "new"
    assert created["suggestedType"] == "bug"
    assert created["suggestedPriority"] == "urgent"
    assert created["aiSummary"]
    assert created["triageMeta"]["provider"] == "rules"

    resp = await owner_client.get(f"/api/v1/projects/{project_id}/intake")
    page = resp.json()["data"]
    assert page["total"] == 1
    assert page["items"][0]["id"] == created["id"]

    resp = await owner_client.get(f"/api/v1/projects/{project_id}/intake?status=new")
    assert resp.json()["data"]["total"] == 1


async def test_accept_creates_intake_sourced_work_item(owner_client: AsyncClient, initialized: SimpleNamespace) -> None:
    created = await _create(owner_client, initialized.project.id)
    resp = await owner_client.post(f"/api/v1/intake/{created['id']}/accept", json={})
    data = resp.json()["data"]
    assert data["status"] == "converted"
    work_item_id = data["convertedWorkItemId"]
    assert work_item_id

    wi = await owner_client.get(f"/api/v1/work-items/{work_item_id}")
    wi_data = wi.json()["data"]
    assert wi_data["source"] == "intake"
    assert wi_data["sourceRefId"] == created["id"]


async def test_reject(owner_client: AsyncClient, initialized: SimpleNamespace) -> None:
    created = await _create(owner_client, initialized.project.id, title="Spam")
    resp = await owner_client.post(f"/api/v1/intake/{created['id']}/reject", json={"reason": "noise"})
    data = resp.json()["data"]
    assert data["status"] == "rejected"
    assert data["rejectionReason"] == "noise"


async def test_get_unknown_returns_not_found(owner_client: AsyncClient, initialized: SimpleNamespace) -> None:
    resp = await owner_client.get("/api/v1/intake/missing_id")
    body = resp.json()
    assert body["code"] == 3001
