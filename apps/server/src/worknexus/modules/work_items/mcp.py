"""work_items MCP sub-server: 6 atomic tools wrapping the service layer.

Identity is resolved from the `X-WorkNexus-Delegation` header via M1's existing
`verify_delegation_token` (tool parameters are never an auth source). The full /mcp
server-token middleware, AgentAction confirmation flow and skill_invocations logging
land in M4/M5 — until then these tools are wired but not yet reachable by a real caller.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.deps import Actor, ActorType
from worknexus.core.errors import BizError
from worknexus.db import get_session_factory
from worknexus.modules.identity import service as identity_service
from worknexus.modules.identity.schemas import DelegationContext
from worknexus.modules.work_items import service
from worknexus.modules.work_items.schemas import (
    CommentCreateIn,
    WorkItemCreateIn,
    WorkItemPriority,
    WorkItemSort,
    WorkItemSource,
    WorkItemStatus,
    WorkItemTransitionIn,
    WorkItemType,
    WorkItemUpdateIn,
)

work_items_mcp: FastMCP = FastMCP("WorkItems")

DELEGATION_HEADER = "x-worknexus-delegation"


@asynccontextmanager
async def _delegated() -> AsyncIterator[tuple[AsyncSession, Actor, DelegationContext]]:
    """Resolve the AI-agent actor from the delegation token and open a session.

    BizError (invalid token / business rule) surfaces to the caller as ToolError."""
    token = get_http_headers().get(DELEGATION_HEADER)
    if not token:
        raise ToolError("missing X-WorkNexus-Delegation token")
    async with get_session_factory()() as db:
        try:
            ctx = await identity_service.verify_delegation_token(db, token)
            actor = Actor(id=ctx.agent_id, type=ActorType.AI_AGENT, tenant_id=ctx.tenant_id)
            yield db, actor, ctx
        except BizError as exc:
            raise ToolError(exc.message) from exc


def _require_project(ctx: DelegationContext) -> str:
    if ctx.project_id is None:
        raise ToolError("delegation token is not bound to a project")
    return ctx.project_id


@work_items_mcp.tool(tags={"low_write"})
async def create_work_item(
    title: str,
    type: str = "task",
    description: str | None = None,
    priority: str = "medium",
    assignee_id: str | None = None,
    tags: list[str] | None = None,
    custom_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a work item in the delegation's project (source=mcp)."""
    async with _delegated() as (db, actor, ctx):
        data = WorkItemCreateIn(
            type=WorkItemType(type),
            title=title,
            description=description,
            priority=WorkItemPriority(priority),
            assignee_id=assignee_id,
            tags=tags or [],
            custom_fields=custom_fields or {},
        )
        result = await service.create_work_item(db, actor, _require_project(ctx), data, source=WorkItemSource.MCP)
        return result.model_dump(mode="json", by_alias=True)


@work_items_mcp.tool(tags={"low_write"})
async def update_work_item(
    work_item_id: str,
    title: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    assignee_id: str | None = None,
    custom_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Update fields of an existing work item."""
    async with _delegated() as (db, actor, _ctx):
        payload: dict[str, Any] = {}
        if title is not None:
            payload["title"] = title
        if description is not None:
            payload["description"] = description
        if priority is not None:
            payload["priority"] = WorkItemPriority(priority)
        if assignee_id is not None:
            payload["assignee_id"] = assignee_id
        if custom_fields is not None:
            payload["custom_fields"] = custom_fields
        result = await service.update_work_item(db, actor, work_item_id, WorkItemUpdateIn(**payload))
        return result.model_dump(mode="json", by_alias=True)


@work_items_mcp.tool(tags={"low_write"})
async def transition_work_item(work_item_id: str, status: str) -> dict[str, Any]:
    """Move a work item to a new status (validated against the fixed state machine)."""
    async with _delegated() as (db, actor, _ctx):
        result = await service.transition_work_item(
            db, actor, work_item_id, WorkItemTransitionIn(status=WorkItemStatus(status))
        )
        return result.model_dump(mode="json", by_alias=True)


@work_items_mcp.tool(tags={"low_write"})
async def comment_work_item(work_item_id: str, body: str) -> dict[str, Any]:
    """Add a Markdown comment authored by the AI agent."""
    async with _delegated() as (db, actor, _ctx):
        result = await service.create_comment(db, actor, work_item_id, CommentCreateIn(body=body))
        return result.model_dump(mode="json", by_alias=True)


@work_items_mcp.tool(tags={"read"})
async def search_work_items(
    status: str | None = None,
    type: str | None = None,
    priority: str | None = None,
    assignee_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Search work items in the delegation's project."""
    from worknexus.core.pagination import PageParams

    async with _delegated() as (db, actor, ctx):
        items, total = await service.list_work_items(
            db,
            actor,
            _require_project(ctx),
            status=WorkItemStatus(status) if status else None,
            type=WorkItemType(type) if type else None,
            priority=WorkItemPriority(priority) if priority else None,
            assignee_id=assignee_id,
            sort=WorkItemSort.CREATED_DESC,
            params=PageParams(page=page, page_size=page_size),
        )
        return {"items": [i.model_dump(mode="json", by_alias=True) for i in items], "total": total}


@work_items_mcp.tool(tags={"read"})
async def get_work_item(work_item_id: str) -> dict[str, Any]:
    """Fetch a single work item by id."""
    async with _delegated() as (db, actor, _ctx):
        result = await service.get_work_item_detail(db, actor, work_item_id)
        return result.model_dump(mode="json", by_alias=True)
