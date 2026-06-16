"""home REST: envelope smoke for the five-card snapshot + auth gate (login only)."""

from types import SimpleNamespace

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

API = "/api/v1"
CARDS = ("myTodos", "overdue", "pendingAgentActions", "recentAiCreated", "pendingIntake")


@pytest.mark.p0
async def test_owner_home_envelope(owner_client: AsyncClient, initialized: SimpleNamespace) -> None:
    pid = initialized.project.id
    await owner_client.post(
        f"{API}/projects/{pid}/work-items",
        json={"type": "task", "title": "x", "assigneeId": initialized.owner.id},
    )

    body = (await owner_client.get(f"{API}/home")).json()
    assert body["code"] == 0
    data = body["data"]
    for card in CARDS:
        assert "total" in data[card] and "items" in data[card]
    assert data["myTodos"]["total"] >= 1


@pytest.mark.p1
async def test_unauthenticated_is_401(client: AsyncClient, initialized: SimpleNamespace) -> None:
    assert (await client.get(f"{API}/home")).status_code == 401
