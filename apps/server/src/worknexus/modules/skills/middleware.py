"""/mcp dual-token gate + skill_invocation logging (M4).

Every MCP tool call passes through `on_call_tool`:
  1. server token (Authorization: Bearer) proves the request comes from multirag
  2. delegation token (X-WorkNexus-Delegation) proves which user/agent it represents
  3. risk gate: read executes; low_write is blocked pending M5 AgentAction; high_write
     and missing permission are rejected
  4. every call (success / failure / blocked / rejected) writes one skill_invocation

Identity is never taken from tool parameters. Rejections happen before `call_next`
(FastMCP only logs — does not deliver — errors raised after call_next).
"""

import json
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Literal

from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.tools import ToolResult
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.config import get_settings
from worknexus.core.access import Permission
from worknexus.core.deps import Actor, ActorType
from worknexus.core.errors import BizError, ErrorCode
from worknexus.db import get_session_factory
from worknexus.modules.identity import service as identity_service
from worknexus.modules.skills import service
from worknexus.modules.skills.context import MCPCallContext, reset_mcp_context, set_mcp_context
from worknexus.modules.skills.reflection import permission_for_tags, risk_for_tags
from worknexus.modules.skills.schemas import RiskLevel, SkillInvocationStatus

DELEGATION_HEADER = "x-worknexus-delegation"
_BEARER_PREFIX = "bearer "
_SUMMARY_LIMIT = 2000

# Tool tags are static; cache the name → tags map after the first reflection.
_tool_tags_cache: dict[str, set[str]] | None = None


# --- pure helpers (unit-tested without HTTP) -------------------------------------


def read_server_token(headers: dict[str, str]) -> str | None:
    """Parse `Authorization: Bearer <token>` (case-insensitive scheme)."""
    raw = headers.get("authorization")
    if not raw or not raw.lower().startswith(_BEARER_PREFIX):
        return None
    return raw[len(_BEARER_PREFIX) :].strip() or None


def verify_server_token(token: str | None, expected: str) -> bool:
    if not token or not expected:
        return False
    return secrets.compare_digest(token, expected)


def read_delegation_token(headers: dict[str, str]) -> str | None:
    return headers.get(DELEGATION_HEADER) or None


def summarize(value: Any, *, limit: int = _SUMMARY_LIMIT) -> str:
    """Compact, redacted summary for storage — never the delegation/server token."""
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, default=str, ensure_ascii=False)
        except (TypeError, ValueError):
            text = str(value)
    return _redact(text)[:limit]


def _redact(text: str) -> str:
    out = []
    for part in text.split():
        if part.startswith("wn_del_") and len(part) > 10:
            out.append("wn_del_***")
        else:
            out.append(part)
    return " ".join(out) if out else text


@dataclass(frozen=True)
class Decision:
    action: Literal["allow", "defer", "rejected"]
    status: SkillInvocationStatus
    error_code: ErrorCode | None = None
    message: str = ""


def decide_execution(
    risk: RiskLevel | None,
    required_permission: Permission | None,
    permissions_snapshot: dict[str, Any],
) -> Decision:
    """D5 double-check: user ∧ agent (effective) ∧ risk. A permitted low_write tool call
    is deferred into a pending AgentAction (M5) rather than blocked; the human confirms it
    before any write. high_write and missing permission are rejected outright."""
    if risk is None:
        return Decision("rejected", SkillInvocationStatus.REJECTED, ErrorCode.FORBIDDEN, "unknown tool risk level")
    if risk == RiskLevel.HIGH_WRITE:
        return Decision(
            "rejected",
            SkillInvocationStatus.REJECTED,
            ErrorCode.SKILL_RISK_FORBIDDEN,
            "high_write actions are not permitted for AI in v0.1",
        )
    effective = set(permissions_snapshot.get("effective", []))
    if required_permission is not None and required_permission.value not in effective:
        return Decision("rejected", SkillInvocationStatus.REJECTED, ErrorCode.FORBIDDEN, "permission denied")
    if risk == RiskLevel.LOW_WRITE:
        return Decision("defer", SkillInvocationStatus.SUCCESS)
    return Decision("allow", SkillInvocationStatus.RUNNING)


# --- session source (injectable for tests) ---------------------------------------


@asynccontextmanager
async def open_session() -> AsyncIterator[AsyncSession]:
    async with get_session_factory()() as session:
        yield session


async def _tool_tags(tool_name: str) -> set[str]:
    global _tool_tags_cache
    if _tool_tags_cache is None:
        from worknexus.mcp import mcp

        _tool_tags_cache = {tool.name: set(tool.tags or []) for tool in await mcp.list_tools()}
    return _tool_tags_cache.get(tool_name, set())


# --- middleware ------------------------------------------------------------------


class SkillInvocationMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext[Any], call_next: Any) -> Any:
        headers = get_http_headers(include={"authorization"})
        settings = get_settings()

        if not verify_server_token(read_server_token(headers), settings.mcp_auth_token):
            raise ToolError("MCP server token invalid")
        delegation_token = read_delegation_token(headers)
        if not delegation_token:
            raise ToolError("missing X-WorkNexus-Delegation token")

        tool_name = context.message.name
        arguments = context.message.arguments or {}
        tags = await _tool_tags(tool_name)
        risk = risk_for_tags(tags)
        required_permission = permission_for_tags(tags)

        async with open_session() as log_db:
            try:
                delegation = await identity_service.verify_delegation_token(log_db, delegation_token)
            except BizError as exc:
                raise ToolError(exc.message) from exc
            actor = Actor(id=delegation.agent_id, type=ActorType.AI_AGENT, tenant_id=delegation.tenant_id)
            decision = decide_execution(risk, required_permission, delegation.permissions_snapshot)

            inv = await service.begin_invocation(
                log_db,
                actor,
                delegation=delegation,
                tool_name=tool_name,
                risk_level=risk if risk is not None else RiskLevel.HIGH_WRITE,
                requires_confirmation=risk == RiskLevel.LOW_WRITE,
                input_summary=summarize(arguments),
            )

            if decision.action == "rejected":
                await service.finish_invocation(log_db, inv, status=decision.status, error_message=decision.message)
                await log_db.commit()
                raise ToolError(decision.message)

            if decision.action == "defer":
                # Permitted low_write call: normalize it into a pending AgentAction for human
                # confirmation instead of executing. Return a normal result so the model can
                # tell the user it's queued (M5 — replaces M4's "blocked" ToolError).
                from worknexus.modules.workchat import service as workchat_service

                try:
                    action = await workchat_service.create_pending_agent_action(
                        log_db,
                        delegation,
                        tool_name=tool_name,
                        arguments=dict(arguments),
                        skill_invocation_id=inv.id,
                    )
                except BizError as exc:
                    await service.finish_invocation(
                        log_db, inv, status=SkillInvocationStatus.FAILED, error_message=exc.message
                    )
                    await log_db.commit()
                    raise ToolError(exc.message) from exc
                inv.agent_action_id = action.id
                await service.finish_invocation(
                    log_db, inv, status=decision.status, output_summary=f"pending agent_action {action.id}"
                )
                await log_db.commit()
                return ToolResult(
                    content=(
                        f"Action queued for human confirmation in WorkNexus (agent_action {action.id}); "
                        "not yet executed."
                    ),
                    structured_content={
                        "status": "pending_confirmation",
                        "agentActionId": action.id,
                        "requiresConfirmation": True,
                    },
                )

            async with open_session() as business_db:
                token = set_mcp_context(MCPCallContext(db=business_db, actor=actor, delegation=delegation))
                try:
                    result = await call_next(context)
                except Exception as exc:
                    await service.finish_invocation(
                        log_db, inv, status=SkillInvocationStatus.FAILED, error_message=summarize(str(exc))
                    )
                    await log_db.commit()
                    raise
                finally:
                    reset_mcp_context(token)
                await service.finish_invocation(
                    log_db, inv, status=SkillInvocationStatus.SUCCESS, output_summary=summarize(result)
                )
                await log_db.commit()
                return result
