"""workchat REST smoke: conversations, messages, and the agent-action approve flow.

The pending AgentAction is created directly via the service (the AI run that normally
produces it lands in PR3); here we verify the REST surface end to end.
"""

import json
from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.modules.identity.schemas import DelegationContext
from worknexus.modules.workchat import service

pytestmark = [pytest.mark.p1, pytest.mark.integration]


async def _propose_create_work_item(db: AsyncSession, initialized: SimpleNamespace) -> str:
    delegation = DelegationContext(
        tenant_id=initialized.tenant.id,
        user_id=initialized.owner.id,
        agent_id=initialized.agent.id,
        project_id=initialized.project.id,
        conversation_id=None,
        run_id=None,
        permissions_snapshot={"user": [], "agent": [], "effective": ["work_item.create"]},
    )
    action = await service.create_pending_agent_action(
        db,
        delegation,
        tool_name="workitem_create_work_item",
        arguments={"title": "AI proposed task", "type": "task"},
        skill_invocation_id="si_rest_0001",
    )
    await db.commit()
    return action.id


async def test_conversations_and_messages(
    owner_client: AsyncClient, db: AsyncSession, initialized: SimpleNamespace
) -> None:
    project_id = initialized.project.id
    resp = await owner_client.get(f"/api/v1/projects/{project_id}/conversations")
    body = resp.json()
    assert body["code"] == 0
    conversations = body["data"]
    assert len(conversations) == 1
    conversation_id = conversations[0]["id"]

    resp = await owner_client.post(f"/api/v1/conversations/{conversation_id}/messages", json={"content": "hello AI"})
    assert resp.json()["code"] == 0

    resp = await owner_client.get(f"/api/v1/conversations/{conversation_id}/messages")
    page = resp.json()["data"]
    assert page["total"] == 1
    assert page["items"][0]["content"] == "hello AI"
    assert page["items"][0]["role"] == "user"


async def test_approve_agent_action_creates_work_item(
    owner_client: AsyncClient, db: AsyncSession, initialized: SimpleNamespace
) -> None:
    action_id = await _propose_create_work_item(db, initialized)

    listed = (await owner_client.get("/api/v1/agent-actions?status=pending")).json()["data"]
    assert listed["total"] == 1
    assert listed["items"][0]["id"] == action_id

    resp = await owner_client.post(f"/api/v1/agent-actions/{action_id}/approve")
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["status"] == "executed"
    assert body["data"]["resultRefType"] == "work_item"
    assert body["data"]["approvedByUserId"] == initialized.owner.id


async def test_reject_agent_action(owner_client: AsyncClient, db: AsyncSession, initialized: SimpleNamespace) -> None:
    action_id = await _propose_create_work_item(db, initialized)
    resp = await owner_client.post(f"/api/v1/agent-actions/{action_id}/reject", json={"reason": "not now"})
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["status"] == "rejected"
    assert body["data"]["rejectionReason"] == "not now"


async def test_run_streams_sse(
    owner_client: AsyncClient, db: AsyncSession, monkeypatch: pytest.MonkeyPatch, initialized: SimpleNamespace
) -> None:
    from worknexus.modules.workchat import router as workchat_router
    from worknexus.modules.workchat.ai_client import DoneEvent, FakeAIClient, TextDelta

    # Default settings are multirag mode, so the resolved agent needs an external id.
    initialized.agent.external_agent_id = "multirag-ext-test"
    await db.commit()
    monkeypatch.setattr(workchat_router, "get_ai_client", lambda settings: FakeAIClient([TextDelta("hi"), DoneEvent()]))
    project_id = initialized.project.id
    conversation_id = (await owner_client.get(f"/api/v1/projects/{project_id}/conversations")).json()["data"][0]["id"]

    collected = []
    async with owner_client.stream(
        "POST", "/api/v1/workchat/runs", json={"conversationId": conversation_id, "content": "hi"}
    ) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        async for line in resp.aiter_lines():
            if line.startswith("data:"):
                collected.append(json.loads(line[len("data:") :].strip()))

    types = [event["type"] for event in collected]
    assert "message_delta" in types
    assert types[-1] == "done"
