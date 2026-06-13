from fastmcp import FastMCP

from worknexus.modules.system.mcp import system_mcp
from worknexus.modules.work_items.mcp import work_items_mcp

mcp: FastMCP = FastMCP("WorkNexus")
mcp.mount(system_mcp, namespace="system")
mcp.mount(work_items_mcp, namespace="workitem")
