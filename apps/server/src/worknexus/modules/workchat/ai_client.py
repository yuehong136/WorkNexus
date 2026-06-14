"""AI Adapter: a thin client over the multirag platform's streaming completions.

WorkNexus owns "data / permission / confirmation / execution / audit"; this module only
calls multirag's SSE endpoint and normalizes its frames into `AIEvent`s. The wire format
was reverse-engineered from the multirag reference frontend (ts/web): an envelope
`{retcode, retmsg?, data}` where `data` is `true` (end) | a string (legacy text) |
`{type, content}` with type in text / tool_call / tool_result / tool_start / tool_end /
error / metadata. multirag never emits a `proposed_action` frame — a proposed action is
the AI calling a low_write WorkNexus MCP tool (handled server-side by the skills
middleware); here we only surface the resulting tool_result.

`AIClient` is a Protocol so tests/E2E inject `FakeAIClient`. The real endpoint/body must be
live-verified before relying on `MultiragAgentCompletionsClient` — see docs §11.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

import httpx

from worknexus.config import Settings

# --- normalized events -----------------------------------------------------------


@dataclass(frozen=True)
class TextDelta:
    content: str


@dataclass(frozen=True)
class ToolCall:
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    call_id: str | None = None


@dataclass(frozen=True)
class ToolResultEvent:
    tool_name: str
    call_id: str | None
    result: Any
    success: bool = True
    error: str | None = None


@dataclass(frozen=True)
class KnowledgeEvent:
    references: list[dict[str, Any]]


@dataclass(frozen=True)
class ErrorEvent:
    message: str
    code: int | None = None


@dataclass(frozen=True)
class ProposeAction:
    """Fake-only: asks the orchestration to create a pending AgentAction directly.

    The real MultiragAgentCompletionsClient never emits this — in production a proposal is
    the AI calling a low_write MCP tool, gated and created by the skills middleware, and
    surfaced here as a ToolResultEvent. This exists so the FakeAIClient can drive the full
    confirmation chain in tests/E2E without a live multirag + /mcp round trip."""

    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DoneEvent:
    pass


AIEvent = TextDelta | ToolCall | ToolResultEvent | KnowledgeEvent | ErrorEvent | ProposeAction | DoneEvent


# --- pure parser (unit-tested with fixtures) -------------------------------------


def parse_sse_frame(raw: str) -> AIEvent | None:
    """Map one SSE `data:` payload (a JSON envelope) to an AIEvent, or None to skip.

    Tolerant by design: unknown frame types and malformed JSON are skipped, not raised —
    a single bad frame must not abort a run."""
    raw = raw.strip()
    if not raw or raw == "[DONE]":
        return DoneEvent() if raw == "[DONE]" else None
    try:
        envelope = json.loads(raw)
    except (TypeError, ValueError):
        return None
    if not isinstance(envelope, dict):
        return None

    retcode = envelope.get("retcode")
    if retcode is None:
        retcode = envelope.get("code", 0)
    if retcode not in (0, None):
        try:
            code = int(retcode)
        except (TypeError, ValueError):
            code = None
        return ErrorEvent(message=str(envelope.get("retmsg") or "ai platform error"), code=code)

    data = envelope.get("data")
    if data is True:
        return DoneEvent()
    if isinstance(data, str):
        return TextDelta(content=data) if data else None
    if not isinstance(data, dict):
        return None

    frame_type = data.get("type")
    content = data.get("content")
    if frame_type == "text":
        text = content if isinstance(content, str) else ""
        return TextDelta(content=text) if text else None
    if frame_type == "tool_call" and isinstance(content, dict):
        return ToolCall(
            tool_name=str(content.get("tool_name", "")),
            arguments=content.get("arguments") or {},
            call_id=content.get("call_id"),
        )
    if frame_type == "tool_result" and isinstance(content, dict):
        return ToolResultEvent(
            tool_name=str(content.get("tool_name", "")),
            call_id=content.get("call_id"),
            result=content.get("result"),
            success=bool(content.get("success", True)),
            error=content.get("error"),
        )
    if frame_type == "error":
        message = content.get("error") if isinstance(content, dict) else content
        code = content.get("code") if isinstance(content, dict) else None
        return ErrorEvent(message=str(message or "ai platform error"), code=code)
    if frame_type == "metadata" and isinstance(content, dict) and content.get("references"):
        return KnowledgeEvent(references=list(content["references"]))
    # tool_start / tool_end / metadata-without-refs are progress noise — skip.
    return None


def data_payloads(lines: Iterable[str]) -> list[str]:
    """Extract the JSON payloads from `data:` SSE lines (sync helper for fixtures/tests)."""
    return [line[len("data:") :].strip() for line in lines if line.startswith("data:")]


# --- client protocol -------------------------------------------------------------


@runtime_checkable
class AIClient(Protocol):
    # Non-async signature: implementations are async generators, whose type is
    # `(...) -> AsyncIterator[AIEvent]` (not a coroutine returning one).
    def stream_run(
        self,
        *,
        messages: list[dict[str, str]],
        context: dict[str, Any],
        delegation_token: str,
        agent_id: str,
    ) -> AsyncIterator[AIEvent]: ...


# --- fake (tests / E2E / offline dev) --------------------------------------------


class FakeAIClient:
    """Deterministic AIClient that replays a scripted list of events. The script is built
    by the caller (tests/E2E); a `tool_result` event referencing a real agentActionId
    drives the proposed-action surface without a live multirag."""

    def __init__(self, script: list[AIEvent] | None = None) -> None:
        self._script = script if script is not None else _default_script()

    async def stream_run(
        self,
        *,
        messages: list[dict[str, str]],
        context: dict[str, Any],
        delegation_token: str,
        agent_id: str,
    ) -> AsyncIterator[AIEvent]:
        for event in self._script:
            yield event


def _default_script() -> list[AIEvent]:
    # Drives the full chain for E2E/offline: a reply + a proposed work item to confirm.
    return [
        TextDelta(content="Sure — I'll draft a work item for that."),
        ProposeAction(
            tool_name="workitem_create_work_item", arguments={"title": "Follow up from WorkChat", "type": "task"}
        ),
        DoneEvent(),
    ]


# --- real multirag client (live-verify endpoint/body before relying on this) -----


class MultiragAgentCompletionsClient:
    """Calls multirag `POST {base}/api/v1/agents/{agent_id}/completions` (SSE).

    TODO(live-verify): confirm the exact path, request body field names, how the
    delegation custom_header is named, and that the SSE envelope matches `parse_sse_frame`
    against a running multirag before relying on this in production (docs §11). The
    business design does not change if only `enhanced_chat_sse` proves available — add a
    compat client, keep this contract."""

    DELEGATION_HEADER = "X-WorkNexus-Delegation"

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.ai_platform_base_url.rstrip("/")
        self._api_key = settings.ai_platform_api_key
        self._timeout = settings.ai_platform_timeout_seconds

    async def stream_run(
        self,
        *,
        messages: list[dict[str, str]],
        context: dict[str, Any],
        delegation_token: str,
        agent_id: str,
    ) -> AsyncIterator[AIEvent]:
        url = f"{self._base_url}/api/v1/agents/{agent_id}/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "text/event-stream",
            self.DELEGATION_HEADER: delegation_token,
        }
        body = {"messages": messages, "context": context, "stream": True}
        async with (
            httpx.AsyncClient(timeout=self._timeout) as client,
            client.stream("POST", url, headers=headers, json=body) as response,
        ):
            if response.status_code >= 400:
                yield ErrorEvent(message=f"ai platform returned {response.status_code}", code=response.status_code)
                return
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                event = parse_sse_frame(line[len("data:") :])
                if event is not None:
                    yield event


def get_ai_client(settings: Settings) -> AIClient:
    if settings.ai_client == "fake":
        return FakeAIClient()
    return MultiragAgentCompletionsClient(settings)
