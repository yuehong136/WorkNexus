"""PATCH /me: self display-name edit (Settings Lite) + audit + validation gate."""

from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.deps import Actor, ActorType
from worknexus.modules.audit.models import AuditLog
from worknexus.modules.identity import service
from worknexus.modules.identity.schemas import ProfileUpdateIn

pytestmark = pytest.mark.integration

API = "/api/v1"


@pytest.mark.p1
async def test_update_display_name_persists(owner_client: AsyncClient, initialized: SimpleNamespace) -> None:
    body = (await owner_client.patch(f"{API}/me", json={"displayName": "Renamed Owner"})).json()
    assert body["code"] == 0
    assert body["data"]["user"]["displayName"] == "Renamed Owner"

    me = (await owner_client.get(f"{API}/me")).json()
    assert me["data"]["user"]["displayName"] == "Renamed Owner"


@pytest.mark.p1
async def test_update_writes_audit(db: AsyncSession, initialized: SimpleNamespace) -> None:
    actor = Actor(id=initialized.owner.id, type=ActorType.USER, tenant_id=initialized.tenant.id)
    await service.update_profile(db, actor, ProfileUpdateIn(display_name="Audited Name"))

    rows = (await db.execute(select(AuditLog).where(AuditLog.action == "user.profile.update"))).scalars().all()
    assert len(rows) == 1
    assert rows[0].resource_id == initialized.owner.id
    assert rows[0].before == {"displayName": "Owner"}
    assert rows[0].after == {"displayName": "Audited Name"}


@pytest.mark.p1
async def test_empty_display_name_rejected(owner_client: AsyncClient, initialized: SimpleNamespace) -> None:
    assert (await owner_client.patch(f"{API}/me", json={"displayName": ""})).status_code == 422


@pytest.mark.p1
async def test_unauthenticated_is_401(client: AsyncClient, initialized: SimpleNamespace) -> None:
    assert (await client.patch(f"{API}/me", json={"displayName": "x"})).status_code == 401
