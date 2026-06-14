"""Run orchestration with the FakeAIClient: streaming, message persistence, D6 context
filtering, and surfacing a server-created AgentAction.
"""

from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.access import Subject, load_subject
from worknexus.core.deps import Actor, ActorType
from worknexus.core.pagination import PageParams
from worknexus.modules.identity.models import User
from worknexus.modules.identity.schemas import DelegationContext
from worknexus.modules.work_items import service as work_items_service
from worknexus.modules.work_items.schemas import WorkItemCreateIn, WorkItemType
from worknexus.modules.workchat import runs, service
from worknexus.modules.workchat.ai_client import DoneEvent, ErrorEvent, FakeAIClient, TextDelta, ToolResultEvent
from worknexus.modules.workchat.models import Conversation
from worknexus.modules.workchat.schemas import MessageRole

pytestmark = pytest.mark.p1


def _user_actor(initialized: SimpleNamespace) -> Actor:
    return Actor(id=initialized.owner.id, type=ActorType.USER, tenant_id=initialized.tenant.id)


async def _setup(db: AsyncSession, initialized: SimpleNamespace) -> tuple[Actor, Subject, Conversation]:
    actor = _user_actor(initialized)
    subject = await load_subject(db, actor)
    conversation = await service.get_or_create_default_conversation(db, actor, initialized.project.id)
    return actor, subject, conversation


async def test_start_run_persists_user_and_ai_messages(db: AsyncSession, initialized: SimpleNamespace) -> None:
    actor, subject, conversation = await _setup(db, initialized)
    client = FakeAIClient([TextDelta("Hello "), TextDelta("there"), DoneEvent()])
    events = [
        e
        async for e in runs.start_run(
            db,
            subject,
            conversation=conversation,
            content="hi",
            work_item_ids=None,
            ai_client=client,
            agent=runs.ResolvedAgent(internal_agent_id=initialized.agent.id, external_agent_id="multirag-ext-1"),
            run_id="run_1",
        )
    ]
    types = [e["type"] for e in events]
    assert "message_delta" in types
    assert types[-2:] == ["message_done", "done"]

    messages, total = await service.list_messages(db, actor, conversation.id, params=PageParams())
    assert total == 2
    ai_message = next(m for m in messages if m.role == MessageRole.AI)
    assert ai_message.content == "Hello there"
    assert ai_message.run_id == "run_1"


async def test_start_run_surfaces_pending_agent_action(db: AsyncSession, initialized: SimpleNamespace) -> None:
    actor, subject, conversation = await _setup(db, initialized)
    delegation = DelegationContext(
        tenant_id=initialized.tenant.id,
        user_id=initialized.owner.id,
        agent_id=initialized.agent.id,
        project_id=initialized.project.id,
        conversation_id=conversation.id,
        run_id="run_2",
        permissions_snapshot={"effective": ["work_item.create"]},
    )
    action = await service.create_pending_agent_action(
        db,
        delegation,
        tool_name="workitem_create_work_item",
        arguments={"title": "AI task", "type": "task"},
        skill_invocation_id="si_run_0001",
    )
    await db.commit()

    client = FakeAIClient(
        [
            TextDelta("I'll create that task. "),
            ToolResultEvent(
                tool_name="workitem_create_work_item",
                call_id="c1",
                result={"status": "pending_confirmation", "agentActionId": action.id, "requiresConfirmation": True},
                success=True,
            ),
            DoneEvent(),
        ]
    )
    events = [
        e
        async for e in runs.start_run(
            db,
            subject,
            conversation=conversation,
            content="make a task",
            work_item_ids=None,
            ai_client=client,
            agent=runs.ResolvedAgent(internal_agent_id=initialized.agent.id, external_agent_id="multirag-ext-1"),
            run_id="run_2",
        )
    ]
    agent_events = [e for e in events if e["type"] == "agent_action"]
    assert len(agent_events) == 1
    assert agent_events[0]["action"]["id"] == action.id
    assert agent_events[0]["action"]["status"] == "pending"

    messages, _ = await service.list_messages(db, actor, conversation.id, params=PageParams())
    ai_message = next(m for m in messages if m.role == MessageRole.AI)
    assert ai_message.agent_action_id == action.id


async def test_start_run_propose_action_creates_and_surfaces(db: AsyncSession, initialized: SimpleNamespace) -> None:
    _, subject, conversation = await _setup(db, initialized)
    # The default fake script emits a ProposeAction (the E2E/offline affordance).
    client = FakeAIClient()
    events = [
        e
        async for e in runs.start_run(
            db,
            subject,
            conversation=conversation,
            content="make a task",
            work_item_ids=None,
            ai_client=client,
            agent=runs.ResolvedAgent(internal_agent_id=initialized.agent.id, external_agent_id="multirag-ext-1"),
            run_id="run_propose",
        )
    ]
    agent_events = [e for e in events if e["type"] == "agent_action"]
    assert len(agent_events) == 1
    assert agent_events[0]["action"]["actionType"] == "create_work_item"
    assert agent_events[0]["action"]["status"] == "pending"


async def test_start_run_emits_error_event(db: AsyncSession, initialized: SimpleNamespace) -> None:
    _, subject, conversation = await _setup(db, initialized)
    client = FakeAIClient([ErrorEvent(message="model exploded", code=42), DoneEvent()])
    events = [
        e
        async for e in runs.start_run(
            db,
            subject,
            conversation=conversation,
            content="hi",
            work_item_ids=None,
            ai_client=client,
            agent=runs.ResolvedAgent(internal_agent_id=initialized.agent.id, external_agent_id="multirag-ext-1"),
            run_id="run_3",
        )
    ]
    errors = [e for e in events if e["type"] == "error"]
    assert errors and errors[0]["message"] == "model exploded"
    assert events[-1]["type"] == "done"


async def test_build_context_includes_project_and_filters_missing(
    db: AsyncSession, initialized: SimpleNamespace
) -> None:
    actor, subject, conversation = await _setup(db, initialized)
    work_item = await work_items_service.create_work_item(
        db, actor, initialized.project.id, WorkItemCreateIn(type=WorkItemType.TASK, title="ctx")
    )
    _, context = await runs.build_context(db, subject, conversation, work_item_ids=[work_item.id, "missing_id"])
    assert context["project"]["id"] == initialized.project.id
    assert len(context["workItems"]) == 1
    assert context["workItems"][0]["id"] == work_item.id


async def test_build_context_excludes_data_user_cannot_read(
    db: AsyncSession, initialized: SimpleNamespace, member_user: User
) -> None:
    owner = _user_actor(initialized)
    conversation = await service.get_or_create_default_conversation(db, owner, initialized.project.id)
    work_item = await work_items_service.create_work_item(
        db, owner, initialized.project.id, WorkItemCreateIn(type=WorkItemType.TASK, title="secret")
    )
    # member_user has no tenant role and no membership in the project → reads nothing here.
    member_actor = Actor(id=member_user.id, type=ActorType.USER, tenant_id=initialized.tenant.id)
    member_subject = await load_subject(db, member_actor)
    _, context = await runs.build_context(db, member_subject, conversation, work_item_ids=[work_item.id])
    assert "project" not in context
    assert "workItems" not in context


async def test_resolve_agent_matches_configured_external_id(db: AsyncSession, initialized: SimpleNamespace) -> None:
    from worknexus.config import get_settings

    initialized.agent.external_agent_id = "multirag-ext-1"
    await db.commit()
    settings = get_settings().model_copy(
        update={"ai_platform_default_agent_id": "multirag-ext-1", "ai_client": "multirag"}
    )
    resolved = await runs.resolve_agent(db, _user_actor(initialized), settings)
    assert resolved.internal_agent_id == initialized.agent.id  # WorkNexus security principal
    assert resolved.external_agent_id == "multirag-ext-1"  # multirag completions target


async def test_resolve_agent_falls_back_to_agent_with_external_id(
    db: AsyncSession, initialized: SimpleNamespace
) -> None:
    from worknexus.config import get_settings

    initialized.agent.external_agent_id = "multirag-ext-2"
    await db.commit()
    # configured id is unset → fall back to the first active agent that has an external id.
    settings = get_settings().model_copy(update={"ai_platform_default_agent_id": "", "ai_client": "multirag"})
    resolved = await runs.resolve_agent(db, _user_actor(initialized), settings)
    assert resolved.internal_agent_id == initialized.agent.id
    assert resolved.external_agent_id == "multirag-ext-2"


async def test_resolve_agent_raises_without_external_id_in_multirag_mode(
    db: AsyncSession, initialized: SimpleNamespace
) -> None:
    from worknexus.config import get_settings
    from worknexus.core.errors import BizError, ErrorCode

    # setup leaves external_agent_id null when no default agent id is configured.
    settings = get_settings().model_copy(update={"ai_platform_default_agent_id": "", "ai_client": "multirag"})
    with pytest.raises(BizError) as exc:
        await runs.resolve_agent(db, _user_actor(initialized), settings)
    assert exc.value.code == ErrorCode.AI_PLATFORM_UNAVAILABLE


async def test_resolve_agent_fake_mode_runs_on_internal_id(db: AsyncSession, initialized: SimpleNamespace) -> None:
    from worknexus.config import get_settings

    settings = get_settings().model_copy(update={"ai_platform_default_agent_id": "", "ai_client": "fake"})
    resolved = await runs.resolve_agent(db, _user_actor(initialized), settings)
    assert resolved.internal_agent_id == initialized.agent.id
    assert resolved.external_agent_id == initialized.agent.id  # placeholder; the fake ignores it


async def test_start_run_signs_delegation_with_internal_id_and_calls_external(
    db: AsyncSession, initialized: SimpleNamespace
) -> None:
    from worknexus.modules.identity.models import McpDelegationToken

    _, subject, conversation = await _setup(db, initialized)

    captured: dict[str, str] = {}

    class _CapturingClient:
        async def stream_run(self, *, messages, context, delegation_token, agent_id):  # type: ignore[no-untyped-def]
            captured["agent_id"] = agent_id
            yield DoneEvent()

    agent = runs.ResolvedAgent(internal_agent_id=initialized.agent.id, external_agent_id="multirag-ext-9")
    async for _ in runs.start_run(
        db,
        subject,
        conversation=conversation,
        content="hi",
        work_item_ids=None,
        ai_client=_CapturingClient(),
        agent=agent,
        run_id="run_split",
    ):
        pass

    # The AIClient is called with the external (multirag) id...
    assert captured["agent_id"] == "multirag-ext-9"
    # ...while the delegation token binds the internal (WorkNexus) agent id.
    token = (await db.execute(select(McpDelegationToken).where(McpDelegationToken.run_id == "run_split"))).scalar_one()
    assert token.agent_id == initialized.agent.id
