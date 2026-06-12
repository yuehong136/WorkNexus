from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastmcp.utilities.lifespan import combine_lifespans

from worknexus.api import api_router
from worknexus.config import get_settings
from worknexus.core.errors import register_exception_handlers
from worknexus.core.request_id import RequestIdMiddleware
from worknexus.db import dispose_engine
from worknexus.mcp import mcp


@asynccontextmanager
async def app_lifespan(_: FastAPI) -> AsyncGenerator[None]:
    yield
    await dispose_engine()


mcp_app = mcp.http_app(path="/")

app = FastAPI(
    title="WorkNexus",
    version="0.1.0",
    lifespan=combine_lifespans(app_lifespan, mcp_app.lifespan),
)

# Dev only: accept any localhost / private-LAN origin on any port (vite hops
# 5173 -> 5174 when busy; teammates hit the dev box via 192.168.x.x).
# Production stays strictly on the cors_origins allowlist.
DEV_CORS_ORIGIN_REGEX = (
    r"^https?://("
    r"localhost|127\.0\.0\.1"
    r"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
    r"|192\.168\.\d{1,3}\.\d{1,3}"
    r")(:\d+)?$"
)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_origin_regex=DEV_CORS_ORIGIN_REGEX if get_settings().environment == "development" else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router)
app.mount("/mcp", mcp_app)
