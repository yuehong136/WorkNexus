from fastmcp import FastMCP

from worknexus.modules.dashboards.mcp import dashboard_mcp
from worknexus.modules.intake.mcp import intake_mcp
from worknexus.modules.skills.middleware import SkillInvocationMiddleware
from worknexus.modules.system.mcp import system_mcp
from worknexus.modules.work_items.mcp import work_items_mcp

mcp: FastMCP = FastMCP("WorkNexus")
mcp.mount(system_mcp, namespace="system")
mcp.mount(work_items_mcp, namespace="workitem")
mcp.mount(intake_mcp, namespace="intake")
mcp.mount(dashboard_mcp, namespace="dashboard")

# Dual-token gate (server token + delegation) + skill_invocation logging for every
# tool call. Registered on the root server so it covers all mounted sub-servers.
mcp.add_middleware(SkillInvocationMiddleware())
