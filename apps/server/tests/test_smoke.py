import pytest
from fastmcp import Client
from httpx import ASGITransport, AsyncClient

from worknexus.main import app
from worknexus.mcp import mcp

pytestmark = pytest.mark.p0


async def test_health_returns_envelope() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["status"] == "ok"


async def test_mcp_ping_in_memory() -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()
        assert any(t.name == "system_ping" for t in tools)
        result = await client.call_tool("system_ping", {})
        assert result.data["status"] == "ok"
