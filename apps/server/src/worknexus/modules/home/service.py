"""home service: cross-project "my work" snapshot.

Read-only and side-effect-free — no commit, no audit, no AgentAction. It orchestrates the
domain read-models owned by work_items / workchat / intake (decision B, mirroring
dashboards.service) and never imports those modules' models. The accessible-project set
mirrors /me and /projects so the three surfaces agree on what the user can see (D6)."""

from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.access import Subject
from worknexus.core.pagination import PageParams
from worknexus.modules.home.schemas import HomeCardOut, HomeSnapshotOut
from worknexus.modules.intake import service as intake_service
from worknexus.modules.projects import service as projects_service
from worknexus.modules.work_items import service as work_items_service
from worknexus.modules.workchat import service as workchat_service
from worknexus.modules.workchat.schemas import AgentActionStatus

HOME_CARD_LIMIT = 8


async def get_home_snapshot(db: AsyncSession, subject: Subject) -> HomeSnapshotOut:
    actor = subject.actor
    pids = projects_service.accessible_project_ids(subject)

    todos, todos_total = await work_items_service.list_assigned_open_work_items(
        db, actor, project_ids=pids, limit=HOME_CARD_LIMIT
    )
    overdue, overdue_total = await work_items_service.list_my_overdue_work_items(
        db, actor, project_ids=pids, limit=HOME_CARD_LIMIT
    )
    actions, actions_total = await workchat_service.list_agent_actions(
        db,
        actor,
        accessible_project_ids=pids,
        params=PageParams(page=1, page_size=HOME_CARD_LIMIT),
        status=AgentActionStatus.PENDING,
    )
    recent, recent_total = await work_items_service.list_recent_ai_created_work_items(
        db, actor, project_ids=pids, limit=HOME_CARD_LIMIT
    )
    intake, intake_total = await intake_service.list_pending_intake(db, actor, project_ids=pids, limit=HOME_CARD_LIMIT)

    return HomeSnapshotOut(
        my_todos=HomeCardOut(total=todos_total, items=todos),
        overdue=HomeCardOut(total=overdue_total, items=overdue),
        pending_agent_actions=HomeCardOut(total=actions_total, items=actions),
        recent_ai_created=HomeCardOut(total=recent_total, items=recent),
        pending_intake=HomeCardOut(total=intake_total, items=intake),
    )
