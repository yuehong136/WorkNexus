"""Comments / activities / relations tests against real PostgreSQL (rollback fixture)."""

from types import SimpleNamespace
from typing import Any

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

API = "/api/v1"


async def _create(client: AsyncClient, project_id: str, **body: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"type": "task", "title": "Item", **body}
    resp = await client.post(f"{API}/projects/{project_id}/work-items", json=payload)
    data: dict[str, Any] = resp.json()["data"]
    return data


@pytest.mark.p1
async def test_comment_create_and_list(owner_client: AsyncClient, initialized: SimpleNamespace) -> None:
    pid = initialized.project.id
    item_id = (await _create(owner_client, pid))["id"]
    created = await owner_client.post(f"{API}/work-items/{item_id}/comments", json={"body": "**hello** world"})
    assert created.json()["data"]["authorType"] == "user"
    assert created.json()["data"]["author"]["displayName"] == "Owner"
    listed = (await owner_client.get(f"{API}/work-items/{item_id}/comments")).json()["data"]
    assert len(listed) == 1
    assert listed[0]["body"] == "**hello** world"


@pytest.mark.p1
async def test_activity_timeline_records_changes(owner_client: AsyncClient, initialized: SimpleNamespace) -> None:
    pid = initialized.project.id
    item_id = (await _create(owner_client, pid))["id"]
    await owner_client.post(f"{API}/work-items/{item_id}/transition", json={"status": "todo"})
    await owner_client.patch(f"{API}/work-items/{item_id}", json={"title": "Renamed"})
    activities = (await owner_client.get(f"{API}/work-items/{item_id}/activities")).json()["data"]
    actions = [a["action"] for a in activities]
    assert actions[0] == "created"
    assert {"status_changed", "title_changed"}.issubset(set(actions))


@pytest.mark.p1
async def test_relation_lifecycle(owner_client: AsyncClient, initialized: SimpleNamespace) -> None:
    pid = initialized.project.id
    source = (await _create(owner_client, pid, title="Source"))["id"]
    target = (await _create(owner_client, pid, title="Target"))["id"]

    created = await owner_client.post(
        f"{API}/work-items/{source}/relations", json={"type": "blocks", "targetWorkItemId": target}
    )
    rel = created.json()["data"]
    assert rel["direction"] == "outgoing"
    assert rel["related"]["id"] == target

    # outgoing on source, inverse-visible incoming on target
    src_rels = (await owner_client.get(f"{API}/work-items/{source}/relations")).json()["data"]
    assert src_rels[0]["direction"] == "outgoing" and src_rels[0]["type"] == "blocks"
    tgt_rels = (await owner_client.get(f"{API}/work-items/{target}/relations")).json()["data"]
    assert len(tgt_rels) == 1 and tgt_rels[0]["direction"] == "incoming"

    # duplicate same relation rejected
    dup = await owner_client.post(
        f"{API}/work-items/{source}/relations", json={"type": "blocks", "targetWorkItemId": target}
    )
    assert dup.json()["code"] == 2006

    # delete clears it
    relation_id = rel["id"]
    assert (await owner_client.delete(f"{API}/work-items/{source}/relations/{relation_id}")).json()["code"] == 0
    assert (await owner_client.get(f"{API}/work-items/{source}/relations")).json()["data"] == []


@pytest.mark.p1
async def test_relation_rejects_self_nonmanual_and_cross_project(
    owner_client: AsyncClient, initialized: SimpleNamespace
) -> None:
    pid = initialized.project.id
    source = (await _create(owner_client, pid))["id"]

    self_link = await owner_client.post(
        f"{API}/work-items/{source}/relations", json={"type": "relates_to", "targetWorkItemId": source}
    )
    assert self_link.json()["code"] == 2005

    target = (await _create(owner_client, pid))["id"]
    non_manual = await owner_client.post(
        f"{API}/work-items/{source}/relations", json={"type": "blocked_by", "targetWorkItemId": target}
    )
    assert non_manual.json()["code"] == 2005

    other_project = (await owner_client.post(f"{API}/projects", json={"name": "Other", "key": "OTH"})).json()["data"][
        "id"
    ]
    other_item = (await _create(owner_client, other_project))["id"]
    cross = await owner_client.post(
        f"{API}/work-items/{source}/relations", json={"type": "relates_to", "targetWorkItemId": other_item}
    )
    assert cross.json()["code"] == 2005
