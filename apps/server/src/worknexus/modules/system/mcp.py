from typing import Any

from fastmcp import FastMCP

system_mcp: FastMCP = FastMCP("System")


@system_mcp.tool(tags={"read"})
async def ping() -> dict[str, Any]:
    """Verify WorkNexus MCP connectivity."""
    return {"status": "ok", "service": "worknexus"}
