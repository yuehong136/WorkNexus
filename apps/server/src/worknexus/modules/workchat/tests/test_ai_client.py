"""parse_sse_frame: map the reverse-engineered multirag SSE envelope to AIEvents.

Pure-function fixtures — the wire format these assert against is what the real
MultiragAgentCompletionsClient must produce (live-verify before relying on it, docs §11).
"""

import pytest

from worknexus.modules.workchat.ai_client import (
    DoneEvent,
    ErrorEvent,
    FakeAIClient,
    KnowledgeEvent,
    TextDelta,
    ToolCall,
    ToolResultEvent,
    data_payloads,
    parse_sse_frame,
)

pytestmark = pytest.mark.p1


def test_parse_text_frame() -> None:
    event = parse_sse_frame('{"retcode":0,"data":{"type":"text","content":"hello"}}')
    assert isinstance(event, TextDelta)
    assert event.content == "hello"


def test_parse_legacy_string_frame() -> None:
    event = parse_sse_frame('{"retcode":0,"data":"partial text"}')
    assert isinstance(event, TextDelta)
    assert event.content == "partial text"


def test_parse_done_boolean() -> None:
    assert isinstance(parse_sse_frame('{"retcode":0,"data":true}'), DoneEvent)


def test_parse_tool_call() -> None:
    event = parse_sse_frame(
        '{"retcode":0,"data":{"type":"tool_call","content":'
        '{"tool_name":"workitem_create_work_item","arguments":{"title":"x"},"call_id":"c1"}}}'
    )
    assert isinstance(event, ToolCall)
    assert event.tool_name == "workitem_create_work_item"
    assert event.arguments == {"title": "x"}
    assert event.call_id == "c1"


def test_parse_tool_result_carries_pending_action() -> None:
    event = parse_sse_frame(
        '{"retcode":0,"data":{"type":"tool_result","content":'
        '{"tool_name":"workitem_create_work_item","call_id":"c1","success":true,'
        '"result":{"status":"pending_confirmation","agentActionId":"aa1","requiresConfirmation":true}}}}'
    )
    assert isinstance(event, ToolResultEvent)
    assert event.success is True
    assert event.result["agentActionId"] == "aa1"


def test_parse_error_by_retcode() -> None:
    event = parse_sse_frame('{"retcode":500,"retmsg":"boom","data":""}')
    assert isinstance(event, ErrorEvent)
    assert event.code == 500
    assert "boom" in event.message


def test_parse_error_frame_type() -> None:
    event = parse_sse_frame('{"retcode":0,"data":{"type":"error","content":{"error":"nope","code":42}}}')
    assert isinstance(event, ErrorEvent)
    assert "nope" in event.message


def test_parse_knowledge_metadata() -> None:
    event = parse_sse_frame('{"retcode":0,"data":{"type":"metadata","content":{"references":[{"title":"doc"}]}}}')
    assert isinstance(event, KnowledgeEvent)
    assert event.references == [{"title": "doc"}]


@pytest.mark.parametrize(
    "raw",
    [
        '{"retcode":0,"data":{"type":"tool_start","content":"thinking"}}',
        '{"retcode":0,"data":{"type":"tool_end","content":{"total_calls":1}}}',
        '{"retcode":0,"data":{"type":"text","content":""}}',
        '{"retcode":0,"data":{"type":"metadata","content":{"token_count":12}}}',
        "",
        "not json at all",
    ],
)
def test_parse_skips_noise(raw: str) -> None:
    assert parse_sse_frame(raw) is None


def test_data_payloads_extracts_data_lines() -> None:
    lines = ['data: {"a":1}', "event: ping", "data: true", "garbage"]
    assert data_payloads(lines) == ['{"a":1}', "true"]


async def test_fake_client_replays_script() -> None:
    client = FakeAIClient([TextDelta("hi"), DoneEvent()])
    events = [e async for e in client.stream_run(messages=[], context={}, delegation_token="t", agent_id="a")]
    assert events == [TextDelta("hi"), DoneEvent()]
