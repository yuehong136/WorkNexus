"""The two intake AgentActions wired into the M5 confirmation chain: propose →
approve_and_execute dispatches to intake.service as the AI-agent actor."""

from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.deps import Actor, ActorType
from worknexus.modules.identity.schemas import DelegationContext
from worknexus.modules.intake import service as intake_service
from worknexus.modules.intake.models import IntakeRequest
from worknexus.modules.intake.schemas import IntakeCreateIn, IntakeSource, IntakeStatus
from worknexus.modules.work_items.models import WorkItem
from worknexus.modules.work_items.schemas import WorkItemSource, WorkItemType
from worknexus.modules.workchat import service as workchat_service
from worknexus.modules.workchat.models import AgentAction
from worknexus.modules.workchat.schemas import AgentActionStatus, AgentActionType

pytestmark = pytest.mark.p1


def _user_actor(initialized: SimpleNamespace) -> Actor:
    return Actor(id=initialized.owner.id, type=ActorType.USER, tenant_id=initialized.tenant.id)


def _delegation(initialized: SimpleNamespace, effective: list[str]) -> DelegationContext:
    return DelegationContext(
        tenant_id=initialized.tenant.id,
        user_id=initialized.owner.id,
        agent_id=initialized.agent.id,
        project_id=initialized.project.id,
        conversation_id=None,
        run_id=None,
        permissions_snapshot={"user": [], "agent": [], "effective": effective},
    )


async def _propose(
    db: AsyncSession,
    initialized: SimpleNamespace,
    *,
    tool: str,
    arguments: dict[str, Any],
    effective: list[str],
) -> AgentAction:
    action = await workchat_service.create_pending_agent_action(
        db,
        _delegation(initialized, effective),
        tool_name=tool,
        arguments=arguments,
        skill_invocation_id="si_intake_0001",
    )
    await db.commit()
    return action


async def test_create_intake_request_dispatch(db: AsyncSession, initialized: SimpleNamespace) -> None:
    action = await _propose(
        db,
        initialized,
        tool="intake_create_intake_request",
        arguments={"title": "AI-logged request", "description": "please add export"},
        effective=["intake.create"],
    )
    assert action.action_type == AgentActionType.CREATE_INTAKE_REQUEST

    out = await workchat_service.approve_and_execute(db, _user_actor(initialized), action.id)
    assert out.status == AgentActionStatus.EXECUTED
    assert out.result_ref_type == "intake_request"

    intake = await db.get(IntakeRequest, out.result_ref_id)
    assert intake is not None
    # AI-proposed intake is ai_chat-sourced, ref'd to the action, submitter = requesting user.
    assert intake.source == IntakeSource.AI_CHAT
    assert intake.source_ref_id == action.id
    assert intake.submitter_id == initialized.owner.id
    assert intake.status == IntakeStatus.NEW


async def test_accept_intake_request_dispatch(db: AsyncSession, initialized: SimpleNamespace) -> None:
    # An existing (human-logged) intake to accept.
    intake = await intake_service.create_intake_request(
        db,
        _user_actor(initialized),
        initialized.project.id,
        IntakeCreateIn(title="Login crash", description="urgent bug"),
    )

    action = await _propose(
        db,
        initialized,
        tool="intake_accept_intake_request",
        arguments={"intake_request_id": intake.id},
        effective=["intake.triage"],
    )
    assert action.action_type == AgentActionType.ACCEPT_INTAKE_REQUEST

    out = await workchat_service.approve_and_execute(db, _user_actor(initialized), action.id)
    assert out.status == AgentActionStatus.EXECUTED
    assert out.result_ref_type == "work_item"

    work_item = await db.get(WorkItem, out.result_ref_id)
    assert work_item is not None
    assert work_item.source == WorkItemSource.INTAKE
    assert work_item.source_ref_id == intake.id
    assert work_item.type == WorkItemType.BUG
    # reporter is the original submitter (a real users FK), not the AI agent.
    assert work_item.reporter_id == initialized.owner.id

    refreshed = await db.get(IntakeRequest, intake.id)
    assert refreshed is not None
    assert refreshed.status == IntakeStatus.CONVERTED
    assert refreshed.converted_work_item_id == work_item.id
