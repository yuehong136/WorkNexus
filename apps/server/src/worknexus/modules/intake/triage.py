"""Rule-based intake triage (decision A): advisory suggestions only.

A replaceable provider behind the `TriageEngine` Protocol. v0.1 ships `RuleBasedTriageEngine`
(deterministic keyword heuristics, no external dependency, E2E-safe); a `MultiragTriageEngine`
slots in via `get_triage_engine` once the M5 multirag endpoint is live-verified. Suggestions
never auto-apply — the service stores them for display and prefilling the convert form, and
every suggestion carries provenance (`provider`/`version`/`reason`/`confidence`) so a later
switch of provider stays auditable. The engine itself is time-free (the service stamps
`generatedAt` into `triage_meta`) so it stays trivially unit-testable. It never guesses an
assignee — the service validates any suggested assignee against project membership.
"""

from collections.abc import Sequence
from typing import Protocol

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.config import Settings
from worknexus.modules.work_items.schemas import WorkItemPriority, WorkItemType


class TriageSuggestion(BaseModel):
    summary: str | None = None
    category: str | None = None
    suggested_type: WorkItemType | None = None
    suggested_priority: WorkItemPriority | None = None
    suggested_assignee_id: str | None = None
    provider: str
    version: str
    reason: str | None = None
    confidence: float | None = None


class TriageEngine(Protocol):
    async def suggest(
        self,
        db: AsyncSession,
        *,
        project_id: str,
        tenant_id: str,
        title: str,
        description: str | None,
    ) -> TriageSuggestion: ...


# Ordered: first matching bucket wins. Keywords are matched case-insensitively against
# the lowercased title+description (English + 简体中文 signals).
_TYPE_KEYWORDS: list[tuple[WorkItemType, tuple[str, ...]]] = [
    (WorkItemType.INCIDENT, ("incident", "outage", "down", "事故", "宕机", "中断", "线上故障")),
    (WorkItemType.BUG, ("bug", "error", "crash", "broken", "fail", "exception", "报错", "崩溃", "故障", "无法")),
    (WorkItemType.RISK, ("risk", "security", "vulnerab", "compliance", "风险", "安全", "漏洞", "合规")),
    (WorkItemType.REQUIREMENT, ("feature", "request", "need", "需求", "希望", "增加", "新增", "建议加")),
    (WorkItemType.FEEDBACK, ("feedback", "complaint", "反馈", "意见", "吐槽")),
]

_PRIORITY_KEYWORDS: list[tuple[WorkItemPriority, tuple[str, ...]]] = [
    (WorkItemPriority.URGENT, ("urgent", "asap", "immediately", "p0", "blocker", "critical", "紧急", "立刻", "马上")),
    (WorkItemPriority.HIGH, ("important", "high priority", "soon", "p1", "重要", "尽快", "优先")),
    (WorkItemPriority.LOW, ("minor", "trivial", "whenever", "low priority", "p3", "次要", "不急", "有空")),
]


def _summarize(title: str, description: str | None) -> str:
    title = title.strip()
    if not description or not description.strip():
        return title
    first = description.strip().split("\n", 1)[0].strip()
    for sep in (". ", "。", "! ", "！", "? ", "？"):  # noqa: RUF001 (intentional CJK punctuation)
        if sep in first:
            first = first.split(sep, 1)[0].strip()
            break
    snippet = first[:200].strip()
    return f"{title} — {snippet}" if snippet else title


def _match[Bucket](text: str, table: Sequence[tuple[Bucket, tuple[str, ...]]]) -> tuple[Bucket | None, str | None]:
    for value, keywords in table:
        hit = next((kw for kw in keywords if kw in text), None)
        if hit is not None:
            return value, hit
    return None, None


class RuleBasedTriageEngine:
    provider = "rules"
    version = "1"

    async def suggest(
        self,
        db: AsyncSession,
        *,
        project_id: str,
        tenant_id: str,
        title: str,
        description: str | None,
    ) -> TriageSuggestion:
        text = f"{title}\n{description or ''}".lower()
        matched: list[str] = []

        wtype, type_hit = _match(text, _TYPE_KEYWORDS)
        if type_hit is not None:
            matched.append(f"type:{type_hit}")
        suggested_type = wtype or WorkItemType.TASK

        priority, prio_hit = _match(text, _PRIORITY_KEYWORDS)
        if prio_hit is not None:
            matched.append(f"priority:{prio_hit}")
        suggested_priority = priority or WorkItemPriority.MEDIUM

        return TriageSuggestion(
            summary=_summarize(title, description),
            category=suggested_type.value,
            suggested_type=suggested_type,
            suggested_priority=suggested_priority,
            # Rules never guess people; validated-member assignment is a human decision in v0.1.
            suggested_assignee_id=None,
            provider=self.provider,
            version=self.version,
            reason=("matched " + ", ".join(matched)) if matched else "no keyword signals; defaults applied",
            confidence=round(min(0.3 + 0.2 * len(matched), 0.9), 2),
        )


def get_triage_engine(settings: Settings) -> TriageEngine:
    """v0.1 only the rule engine. A `MultiragTriageEngine` keyed on
    `settings.intake_triage_provider` slots in here after the M5 endpoint is live-verified."""
    return RuleBasedTriageEngine()
