"""Per-call MCP context shared from the /mcp middleware to the tool body.

FastMCP middleware `ctx.set_state` does not cross mount boundaries (the root
middleware and a mounted sub-server own separate session stores), so we carry
the resolved delegation context in our own ContextVar instead. The middleware
sets it before `call_next`; read tools read it via `require_mcp_context()`.
"""

from contextvars import ContextVar, Token
from dataclasses import dataclass

from fastmcp.exceptions import ToolError
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.deps import Actor
from worknexus.modules.identity.schemas import DelegationContext


@dataclass(frozen=True)
class MCPCallContext:
    db: AsyncSession
    actor: Actor
    delegation: DelegationContext


_ctx_var: ContextVar[MCPCallContext | None] = ContextVar("mcp_call_context", default=None)


def set_mcp_context(ctx: MCPCallContext) -> Token[MCPCallContext | None]:
    return _ctx_var.set(ctx)


def reset_mcp_context(token: Token[MCPCallContext | None]) -> None:
    _ctx_var.reset(token)


def current_mcp_context() -> MCPCallContext | None:
    return _ctx_var.get()


def require_mcp_context() -> MCPCallContext:
    """Tool-side accessor: the middleware must have authenticated this call."""
    ctx = _ctx_var.get()
    if ctx is None:
        raise ToolError("MCP call context unavailable (request did not pass the /mcp middleware)")
    return ctx
