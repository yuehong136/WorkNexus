"""work_items MCP sub-server: 6 atomic tools wrapping the service layer.

Authentication, the dual-token gate, the risk gate and skill_invocation logging all
live in the /mcp `SkillInvocationMiddleware` (M4). Each tool just reads the resolved
`(db, actor, delegation)` the middleware stashed via `require_mcp_context()` — tool
parameters are never an identity source. In M4 only the read tools (search/get) are
reachable; the four low_write tools are blocked by the middleware until the M5
AgentAction confirmation flow lands.
"""

from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from worknexus.modules.identity.schemas import DelegationContext
from worknexus.modules.skills.context import require_mcp_context
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


def _require_project(delegation: DelegationContext) -> str:
    if delegation.project_id is None:
        raise ToolError("delegation token is not bound to a project")
    return delegation.project_id


@work_items_mcp.tool(tags={"low_write", "perm:work_item.create"})
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
    ctx = require_mcp_context()
    data = WorkItemCreateIn(
        type=WorkItemType(type),
        title=title,
        description=description,
        priority=WorkItemPriority(priority),
        assignee_id=assignee_id,
        tags=tags or [],
        custom_fields=custom_fields or {},
    )
    result = await service.create_work_item(
        ctx.db, ctx.actor, _require_project(ctx.delegation), data, source=WorkItemSource.MCP
    )
    return result.model_dump(mode="json", by_alias=True)


@work_items_mcp.tool(tags={"low_write", "perm:work_item.update"})
async def update_work_item(
    work_item_id: str,
    title: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    assignee_id: str | None = None,
    custom_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Update fields of an existing work item."""
    ctx = require_mcp_context()
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
    result = await service.update_work_item(ctx.db, ctx.actor, work_item_id, WorkItemUpdateIn(**payload))
    return result.model_dump(mode="json", by_alias=True)


@work_items_mcp.tool(tags={"low_write", "perm:work_item.transition"})
async def transition_work_item(work_item_id: str, status: str) -> dict[str, Any]:
    """Move a work item to a new status (validated against the fixed state machine)."""
    ctx = require_mcp_context()
    result = await service.transition_work_item(
        ctx.db, ctx.actor, work_item_id, WorkItemTransitionIn(status=WorkItemStatus(status))
    )
    return result.model_dump(mode="json", by_alias=True)


@work_items_mcp.tool(tags={"low_write", "perm:work_item.comment"})
async def comment_work_item(work_item_id: str, body: str) -> dict[str, Any]:
    """Add a Markdown comment authored by the AI agent."""
    ctx = require_mcp_context()
    result = await service.create_comment(ctx.db, ctx.actor, work_item_id, CommentCreateIn(body=body))
    return result.model_dump(mode="json", by_alias=True)


@work_items_mcp.tool(tags={"read", "perm:work_item.read"})
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

    ctx = require_mcp_context()
    items, total = await service.list_work_items(
        ctx.db,
        ctx.actor,
        _require_project(ctx.delegation),
        status=WorkItemStatus(status) if status else None,
        type=WorkItemType(type) if type else None,
        priority=WorkItemPriority(priority) if priority else None,
        assignee_id=assignee_id,
        sort=WorkItemSort.CREATED_DESC,
        params=PageParams(page=page, page_size=page_size),
    )
    return {"items": [i.model_dump(mode="json", by_alias=True) for i in items], "total": total}


@work_items_mcp.tool(tags={"read", "perm:work_item.read"})
async def get_work_item(work_item_id: str) -> dict[str, Any]:
    """Fetch a single work item by id."""
    ctx = require_mcp_context()
    result = await service.get_work_item_detail(ctx.db, ctx.actor, work_item_id)
    return result.model_dump(mode="json", by_alias=True)
