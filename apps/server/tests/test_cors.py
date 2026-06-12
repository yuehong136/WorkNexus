"""Dev CORS: any localhost / private-LAN origin is accepted; public origins are not."""

import pytest
from httpx import ASGITransport, AsyncClient

from worknexus.main import app

pytestmark = pytest.mark.p1


async def _preflight(origin: str) -> tuple[int, str | None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.options(
            "/api/v1/setup/status",
            headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
        )
    return resp.status_code, resp.headers.get("access-control-allow-origin")


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://192.168.1.5:5173",
        "http://10.0.0.8:5174",
        "http://172.16.0.2:5173",
    ],
)
async def test_dev_allows_localhost_and_private_lan_origins(origin: str) -> None:
    status, allow_origin = await _preflight(origin)
    assert status == 200
    assert allow_origin == origin


@pytest.mark.parametrize("origin", ["https://evil.example.com", "http://8.8.8.8:5173", "http://172.32.0.1:5173"])
async def test_public_origins_are_rejected(origin: str) -> None:
    status, allow_origin = await _preflight(origin)
    assert status == 400
    assert allow_origin is None
