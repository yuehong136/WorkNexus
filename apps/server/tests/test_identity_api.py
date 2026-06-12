"""REST-level identity tests: setup, login/logout, cookie semantics."""

from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from conftest import OWNER_EMAIL, OWNER_PASSWORD, SETUP_PAYLOAD

pytestmark = pytest.mark.integration

COOKIE_NAME = "worknexus_session"


@pytest.mark.p0
async def test_setup_full_flow(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/setup/status")
    assert resp.json() == {"code": 0, "message": "ok", "data": {"initialized": False}}

    resp = await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    body = resp.json()
    assert resp.status_code == 200
    assert body["code"] == 0
    ctx = body["data"]
    assert ctx["user"]["email"] == OWNER_EMAIL
    assert ctx["user"]["displayName"] == "Owner"
    assert ctx["tenant"]["slug"] == "default"
    assert ctx["roles"] == ["owner"]
    assert "tenant.manage" in ctx["permissions"]
    assert [p["name"] for p in ctx["projects"]] == ["WorkNexus Internal"]
    assert [a["name"] for a in ctx["ai"]["availableAgents"]] == ["WorkNexus Assistant"]

    set_cookie = resp.headers["set-cookie"]
    assert COOKIE_NAME in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Max-Age=604800" in set_cookie
    assert "Secure" not in set_cookie  # not production

    resp = await client.get("/api/v1/setup/status")
    assert resp.json()["data"]["initialized"] is True


@pytest.mark.p0
async def test_setup_is_sealed_after_first_run(client: AsyncClient, initialized: SimpleNamespace) -> None:
    resp = await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    assert resp.status_code == 200
    assert resp.json()["code"] == 4001


@pytest.mark.p1
async def test_setup_rejects_weak_password(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/setup", json={**SETUP_PAYLOAD, "password": "short"})
    assert resp.json()["code"] == 4012


@pytest.mark.p0
async def test_login_sets_cookie_and_returns_context(client: AsyncClient, initialized: SimpleNamespace) -> None:
    resp = await client.post("/api/v1/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD})
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["user"]["email"] == OWNER_EMAIL
    assert COOKIE_NAME in resp.headers["set-cookie"]
    assert client.cookies.get(COOKIE_NAME)


@pytest.mark.p1
async def test_login_wrong_password(client: AsyncClient, initialized: SimpleNamespace) -> None:
    resp = await client.post("/api/v1/auth/login", json={"email": OWNER_EMAIL, "password": "wrong-password"})
    assert resp.status_code == 200
    assert resp.json()["code"] == 4002


@pytest.mark.p1
async def test_login_unknown_email(client: AsyncClient, initialized: SimpleNamespace) -> None:
    resp = await client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "whatever-123"})
    assert resp.json()["code"] == 4002


@pytest.mark.p1
async def test_login_disabled_user(client: AsyncClient, db: AsyncSession, initialized: SimpleNamespace) -> None:
    initialized.owner.status = "disabled"
    await db.flush()
    resp = await client.post("/api/v1/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD})
    assert resp.json()["code"] == 4003


@pytest.mark.p0
async def test_logout_requires_auth(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/auth/logout")
    assert resp.status_code == 401


@pytest.mark.p1
async def test_logout_revokes_session(owner_client: AsyncClient) -> None:
    resp = await owner_client.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    # Cookie deleted by the response; a second logout is unauthenticated.
    resp = await owner_client.post("/api/v1/auth/logout")
    assert resp.status_code == 401


@pytest.mark.p1
async def test_revoked_cookie_is_rejected_even_if_kept(owner_client: AsyncClient) -> None:
    token = owner_client.cookies[COOKIE_NAME]
    await owner_client.post("/api/v1/auth/logout")
    owner_client.cookies.set(COOKIE_NAME, token, domain="test")
    resp = await owner_client.post("/api/v1/auth/logout")
    assert resp.status_code == 401


@pytest.mark.p1
async def test_responses_carry_request_id(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/setup/status")
    assert resp.headers.get("x-request-id")
