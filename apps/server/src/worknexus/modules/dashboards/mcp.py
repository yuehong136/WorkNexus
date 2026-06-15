"""dashboards MCP sub-server: one read tool so AI can read project state in WorkChat.

The dual-token gate, risk gate (read executes directly) and skill_invocation logging all live
in the /mcp `SkillInvocationMiddleware` (M4); the tool just reads the resolved
`(db, actor, delegation)` via `require_mcp_context()`. The project is taken from the delegation
binding — never from a tool parameter (AGENTS §7.3).
"""

from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from worknexus.modules.dashboards import service
from worknexus.modules.identity.schemas import DelegationContext
from worknexus.modules.skills.context import require_mcp_context

dashboard_mcp: FastMCP = FastMCP("Dashboard")


def _require_project(delegation: DelegationContext) -> str:
    if delegation.project_id is None:
        raise ToolError("delegation token is not bound to a project")
    return delegation.project_id


@dashboard_mcp.tool(tags={"read", "perm:dashboard.read"})
async def get_project_dashboard(overdue_limit: int = 10) -> dict[str, Any]:
    """Read the dashboard snapshot for the delegation's project: KPIs, status/type/priority/
    source distributions, 7-day created/completed trends, intake counts, workload by assignee,
    a capped overdue preview, and rule-based AI insights."""
    ctx = require_mcp_context()
    snapshot = await service.get_project_dashboard_snapshot(
        ctx.db, ctx.actor, _require_project(ctx.delegation), overdue_limit=overdue_limit
    )
    return snapshot.model_dump(mode="json", by_alias=True)
