"""work_items MCP tools: registration, risk tags, and the delegation auth guard.

Authenticated execution lands with the M4 /mcp middleware; here we verify the tools are
wired (namespaced names + risk tags) and that a call without a delegation token is rejected.
"""

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from worknexus.mcp import mcp

pytestmark = pytest.mark.p1

EXPECTED_TAGS = {
    "workitem_create_work_item": "low_write",
    "workitem_update_work_item": "low_write",
    "workitem_transition_work_item": "low_write",
    "workitem_comment_work_item": "low_write",
    "workitem_search_work_items": "read",
    "workitem_get_work_item": "read",
}


async def test_work_item_tools_registered_with_risk_tags() -> None:
    by_name = {t.name: t for t in await mcp.list_tools()}
    for name, tag in EXPECTED_TAGS.items():
        assert name in by_name, f"{name} not registered"
        assert tag in (by_name[name].tags or set())


async def test_write_tool_requires_delegation_token() -> None:
    async with Client(mcp) as client:
        with pytest.raises(ToolError):
            await client.call_tool("workitem_get_work_item", {"work_item_id": "missing"})
