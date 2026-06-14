"""Pure-function unit tests for the /mcp dual-token gate (no HTTP, no DB)."""

import pytest

from worknexus.core.access import Permission
from worknexus.modules.skills.middleware import (
    decide_execution,
    read_delegation_token,
    read_server_token,
    summarize,
    verify_server_token,
)
from worknexus.modules.skills.reflection import (
    permission_for_tags,
    risk_for_tags,
    skill_code_for_tool,
)
from worknexus.modules.skills.schemas import RiskLevel, SkillInvocationStatus

pytestmark = pytest.mark.p1

_EFFECTIVE = {"effective": ["work_item.create", "work_item.read"]}


@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        ({"authorization": "Bearer abc"}, "abc"),
        ({"authorization": "bearer abc"}, "abc"),
        ({"authorization": "Basic abc"}, None),
        ({"authorization": "Bearer   "}, None),
        ({}, None),
    ],
)
def test_read_server_token(headers: dict[str, str], expected: str | None) -> None:
    assert read_server_token(headers) == expected


@pytest.mark.parametrize(
    ("token", "expected", "ok"),
    [("abc", "abc", True), ("abc", "xyz", False), (None, "abc", False), ("abc", "", False)],
)
def test_verify_server_token(token: str | None, expected: str, ok: bool) -> None:
    assert verify_server_token(token, expected) is ok


def test_read_delegation_token() -> None:
    assert read_delegation_token({"x-worknexus-delegation": "wn_del_x"}) == "wn_del_x"
    assert read_delegation_token({}) is None


def test_risk_for_tags() -> None:
    assert risk_for_tags({"read"}) == RiskLevel.READ
    assert risk_for_tags({"low_write", "perm:work_item.create"}) == RiskLevel.LOW_WRITE
    assert risk_for_tags({"high_write"}) == RiskLevel.HIGH_WRITE
    assert risk_for_tags({"perm:x"}) is None


def test_permission_for_tags() -> None:
    assert permission_for_tags({"perm:work_item.create"}) == Permission.WORK_ITEM_CREATE
    assert permission_for_tags({"read"}) is None
    assert permission_for_tags({"perm:bogus.permission"}) is None


def test_skill_code_for_tool() -> None:
    assert skill_code_for_tool("workitem_create_work_item") == "workitem-skill"
    assert skill_code_for_tool("system_ping") == "system-skill"


def test_decide_execution_read_allows() -> None:
    assert decide_execution(RiskLevel.READ, None, _EFFECTIVE).action == "allow"
    assert decide_execution(RiskLevel.READ, Permission.WORK_ITEM_READ, _EFFECTIVE).action == "allow"


def test_decide_execution_read_missing_permission_rejected() -> None:
    decision = decide_execution(RiskLevel.READ, Permission.AUDIT_READ, _EFFECTIVE)
    assert decision.action == "rejected"
    assert decision.status == SkillInvocationStatus.REJECTED


def test_decide_execution_low_write_blocked_in_m4() -> None:
    decision = decide_execution(RiskLevel.LOW_WRITE, Permission.WORK_ITEM_CREATE, _EFFECTIVE)
    assert decision.action == "blocked"
    assert decision.status == SkillInvocationStatus.BLOCKED


def test_decide_execution_low_write_missing_permission_rejected() -> None:
    decision = decide_execution(RiskLevel.LOW_WRITE, Permission.WORK_ITEM_DELETE, _EFFECTIVE)
    assert decision.action == "rejected"


def test_decide_execution_high_write_always_rejected() -> None:
    decision = decide_execution(RiskLevel.HIGH_WRITE, None, _EFFECTIVE)
    assert decision.action == "rejected"


def test_decide_execution_unknown_risk_rejected() -> None:
    assert decide_execution(None, None, _EFFECTIVE).action == "rejected"


def test_summarize_redacts_delegation_token() -> None:
    assert "wn_del_secrettoken12345" not in summarize("wn_del_secrettoken12345 hello")
    assert summarize({"a": 1}) == '{"a": 1}'
    assert len(summarize("x" * 5000, limit=10)) == 10
