"""intake MCP sub-server: one read tool + two low_write tools.

The dual-token gate, risk gate and skill_invocation logging all live in the /mcp
`SkillInvocationMiddleware` (M4); each tool just reads the resolved `(db, actor, delegation)`
via `require_mcp_context()` — tool parameters are never an identity source. The two low_write
tools (`create_intake_request` / `accept_intake_request`) are the M5-deferred AI actions: the
middleware turns each into a pending AgentAction for human confirmation rather than executing
it; on approval the workchat dispatcher calls back into `intake.service`. reject / duplicate /
snooze are intentionally NOT exposed to AI in v0.1.
"""

from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from worknexus.core.pagination import PageParams
from worknexus.modules.identity.schemas import DelegationContext
from worknexus.modules.intake import service
from worknexus.modules.intake.schemas import IntakeAcceptIn, IntakeCreateIn, IntakeSource, IntakeStatus
from worknexus.modules.skills.context import require_mcp_context
from worknexus.modules.work_items.schemas import WorkItemPriority, WorkItemType

intake_mcp: FastMCP = FastMCP("Intake")


def _require_project(delegation: DelegationContext) -> str:
    if delegation.project_id is None:
        raise ToolError("delegation token is not bound to a project")
    return delegation.project_id


@intake_mcp.tool(tags={"read", "perm:intake.read"})
async def list_intake_requests(
    status: str | None = None,
    source: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """List intake requests in the delegation's project (for AI to reference while triaging)."""
    ctx = require_mcp_context()
    items, total = await service.list_intake_requests(
        ctx.db,
        ctx.actor,
        _require_project(ctx.delegation),
        status=IntakeStatus(status) if status else None,
        source=IntakeSource(source) if source else None,
        params=PageParams(page=page, page_size=page_size),
    )
    return {"items": [i.model_dump(mode="json", by_alias=True) for i in items], "total": total}


@intake_mcp.tool(tags={"low_write", "perm:intake.create"})
async def create_intake_request(title: str, description: str | None = None) -> dict[str, Any]:
    """Log a new intake request in the delegation's project (confirmed via AgentAction)."""
    ctx = require_mcp_context()
    result = await service.create_intake_request(
        ctx.db,
        ctx.actor,
        _require_project(ctx.delegation),
        IntakeCreateIn(title=title, description=description),
        source=IntakeSource.MCP,
    )
    return result.model_dump(mode="json", by_alias=True)


@intake_mcp.tool(tags={"low_write", "perm:intake.triage"})
async def accept_intake_request(
    intake_request_id: str,
    type: str | None = None,
    title: str | None = None,
    priority: str | None = None,
    assignee_id: str | None = None,
) -> dict[str, Any]:
    """Accept an intake request and convert it into a work item (confirmed via AgentAction)."""
    ctx = require_mcp_context()
    result = await service.accept_intake_request(
        ctx.db,
        ctx.actor,
        intake_request_id,
        IntakeAcceptIn(
            type=WorkItemType(type) if type else None,
            title=title,
            priority=WorkItemPriority(priority) if priority else None,
            assignee_id=assignee_id,
        ),
    )
    return result.model_dump(mode="json", by_alias=True)
