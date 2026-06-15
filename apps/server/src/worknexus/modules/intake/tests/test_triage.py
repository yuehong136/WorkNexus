"""Rule-based triage engine: deterministic keyword heuristics + provenance."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.modules.intake.triage import RuleBasedTriageEngine
from worknexus.modules.work_items.schemas import WorkItemPriority, WorkItemType

pytestmark = pytest.mark.p1


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("App crashes on login", WorkItemType.BUG),
        ("Please add a dark mode feature", WorkItemType.REQUIREMENT),
        ("Production outage right now", WorkItemType.INCIDENT),
        ("Security vulnerability in auth", WorkItemType.RISK),
        ("General feedback about the UX", WorkItemType.FEEDBACK),
        ("Do the quarterly cleanup", WorkItemType.TASK),
    ],
)
async def test_rule_engine_type(db: AsyncSession, text: str, expected: WorkItemType) -> None:
    suggestion = await RuleBasedTriageEngine().suggest(db, project_id="p", tenant_id="t", title=text, description=None)
    assert suggestion.suggested_type == expected
    assert suggestion.category == expected.value
    assert suggestion.provider == "rules"
    assert suggestion.version == "1"
    # Rules never guess an assignee.
    assert suggestion.suggested_assignee_id is None
    assert suggestion.summary


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("URGENT: fix this asap", WorkItemPriority.URGENT),
        ("This is important, please handle soon", WorkItemPriority.HIGH),
        ("Minor nit, whenever you get to it", WorkItemPriority.LOW),
        ("A normal request", WorkItemPriority.MEDIUM),
    ],
)
async def test_rule_engine_priority(db: AsyncSession, text: str, expected: WorkItemPriority) -> None:
    suggestion = await RuleBasedTriageEngine().suggest(db, project_id="p", tenant_id="t", title=text, description=None)
    assert suggestion.suggested_priority == expected


async def test_summary_keeps_first_sentence(db: AsyncSession) -> None:
    suggestion = await RuleBasedTriageEngine().suggest(
        db, project_id="p", tenant_id="t", title="Title", description="First sentence here. Second sentence."
    )
    assert "First sentence here" in (suggestion.summary or "")
    assert "Second sentence" not in (suggestion.summary or "")


async def test_confidence_grows_with_matches(db: AsyncSession) -> None:
    none = await RuleBasedTriageEngine().suggest(
        db, project_id="p", tenant_id="t", title="quarterly review", description=None
    )
    both = await RuleBasedTriageEngine().suggest(
        db, project_id="p", tenant_id="t", title="urgent crash", description=None
    )
    assert both.confidence is not None and none.confidence is not None
    assert both.confidence > none.confidence
