from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastmcp.utilities.lifespan import combine_lifespans

from worknexus.api import api_router
from worknexus.config import get_settings
from worknexus.core.errors import register_exception_handlers
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router)
app.mount("/mcp", mcp_app)
