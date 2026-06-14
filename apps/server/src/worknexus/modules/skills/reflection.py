"""Pure reflection of MCP tool tags → skill / risk / required permission.

Single source: a tool declares `tags={"low_write", "perm:work_item.create"}` and
both the /mcp middleware (risk gate) and `GET /skills` derive everything from it.
"""

from collections.abc import Iterable

from worknexus.core.access import Permission
from worknexus.modules.skills.schemas import RiskLevel

PERM_TAG_PREFIX = "perm:"

_RISK_BY_TAG = {r.value: r for r in RiskLevel}


def risk_for_tags(tags: Iterable[str]) -> RiskLevel | None:
    for tag in tags:
        risk = _RISK_BY_TAG.get(tag)
        if risk is not None:
            return risk
    return None


def permission_for_tags(tags: Iterable[str]) -> Permission | None:
    for tag in tags:
        if tag.startswith(PERM_TAG_PREFIX):
            try:
                return Permission(tag.removeprefix(PERM_TAG_PREFIX))
            except ValueError:
                return None
    return None


def skill_code_for_tool(tool_name: str) -> str:
    """`workitem_create_work_item` → `workitem-skill` (namespace is the prefix)."""
    namespace = tool_name.split("_", 1)[0]
    return f"{namespace}-skill"
