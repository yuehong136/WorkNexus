from worknexus.core.schemas import ApiModel
from worknexus.modules.intake.schemas import IntakeOut
from worknexus.modules.work_items.schemas import OverdueWorkItem, WorkItemOut
from worknexus.modules.workchat.schemas import AgentActionOut


class HomeCardOut[T](ApiModel):
    """One workbench card: full count + a top-N preview. `total` is the cross-project total;
    `items` is capped — the UI deep-links to the existing per-project pages for the rest."""

    total: int
    items: list[T]


class HomeSnapshotOut(ApiModel):
    my_todos: HomeCardOut[WorkItemOut]
    overdue: HomeCardOut[OverdueWorkItem]
    pending_agent_actions: HomeCardOut[AgentActionOut]
    recent_ai_created: HomeCardOut[WorkItemOut]
    pending_intake: HomeCardOut[IntakeOut]
