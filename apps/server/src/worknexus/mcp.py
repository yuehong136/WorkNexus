from fastmcp import FastMCP

from worknexus.modules.system.mcp import system_mcp

mcp: FastMCP = FastMCP("WorkNexus")
mcp.mount(system_mcp, namespace="system")
