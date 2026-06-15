"""audit.service.list_audit_logs: filters, pagination, ordering, actor-name resolution,
tenant isolation, and the AI confirmation chain reconstructed by resource filter."""

from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.deps import Actor, ActorType, system_actor
from worknexus.core.pagination import PageParams
from worknexus.modules.audit import service
from worknexus.modules.audit.schemas import AuditActorType, AuditLogOut
from worknexus.modules.audit.service import AuditAction

pytestmark = [pytest.mark.integration, pytest.mark.p1]


def _user_actor(init: SimpleNamespace) -> Actor:
    return Actor(id=init.owner.id, type=ActorType.USER, tenant_id=init.tenant.id)


def _agent_actor(init: SimpleNamespace) -> Actor:
    return Actor(id=init.agent.id, type=ActorType.AI_AGENT, tenant_id=init.tenant.id)


async def _page(
    db: AsyncSession,
    init: SimpleNamespace,
    *,
    actor_type: AuditActorType | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    project_id: str | None = None,
) -> tuple[list[AuditLogOut], int]:
    return await service.list_audit_logs(
        db,
        _user_actor(init),
        params=PageParams(page=1, page_size=50),
        actor_type=actor_type,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        project_id=project_id,
    )


async def test_resolves_actor_display_names(db: AsyncSession, initialized: SimpleNamespace) -> None:
    _, baseline = await _page(db, initialized)  # setup wrote a setup.complete system row
    await service.record(db, _user_actor(initialized), action=AuditAction.WORK_ITEM_CREATE, resource_type="work_item")
    await service.record(
        db, _agent_actor(initialized), action=AuditAction.SKILL_INVOKE, resource_type="skill_invocation"
    )
    await service.record(
        db, system_actor(initialized.tenant.id), action=AuditAction.AUTH_LOGOUT, resource_type="session"
    )

    items, total = await _page(db, initialized)
    assert total == baseline + 3
    by_type = {i.actor.type: i for i in items}
    assert by_type[AuditActorType.USER].actor.display_name == "Owner"
    assert by_type[AuditActorType.AI_AGENT].actor.display_name == initialized.agent.name
    assert by_type[AuditActorType.SYSTEM].actor.display_name is None
    assert by_type[AuditActorType.SYSTEM].actor.id == "system"


async def test_filters_by_actor_type_action_and_resource(db: AsyncSession, initialized: SimpleNamespace) -> None:
    await service.record(
        db, _user_actor(initialized), action=AuditAction.WORK_ITEM_CREATE, resource_type="work_item", resource_id="wi1"
    )
    await service.record(
        db, _agent_actor(initialized), action=AuditAction.WORK_ITEM_CREATE, resource_type="work_item", resource_id="wi2"
    )
    await service.record(db, _user_actor(initialized), action=AuditAction.AUTH_LOGIN, resource_type="session")

    _, only_user = await _page(db, initialized, actor_type=AuditActorType.USER)
    assert only_user == 2
    _, only_login = await _page(db, initialized, action=AuditAction.AUTH_LOGIN)
    assert only_login == 1
    items, total = await _page(db, initialized, resource_type="work_item", resource_id="wi2")
    assert total == 1 and items[0].actor.type == AuditActorType.AI_AGENT


async def test_filters_by_project_and_resolves_project_name(db: AsyncSession, initialized: SimpleNamespace) -> None:
    pid = initialized.project.id
    await service.record(
        db, _user_actor(initialized), action=AuditAction.WORK_ITEM_CREATE, resource_type="work_item", project_id=pid
    )
    await service.record(
        db, _user_actor(initialized), action=AuditAction.AUTH_LOGIN, resource_type="session"
    )  # no project

    items, total = await _page(db, initialized, project_id=pid)
    assert total == 1
    assert items[0].project_id == pid
    assert items[0].project_name == initialized.project.name


async def test_orders_desc_and_paginates(db: AsyncSession, initialized: SimpleNamespace) -> None:
    _, baseline = await _page(db, initialized)
    for _ in range(5):
        await service.record(
            db, _user_actor(initialized), action=AuditAction.WORK_ITEM_CREATE, resource_type="work_item"
        )

    first = await service.list_audit_logs(db, _user_actor(initialized), params=PageParams(page=1, page_size=2))
    assert first[1] == baseline + 5 and len(first[0]) == 2
    times = [i.created_at for i in first[0]]
    assert times == sorted(times, reverse=True)


async def test_tenant_isolation(db: AsyncSession, initialized: SimpleNamespace) -> None:
    _, baseline = await _page(db, initialized)
    await service.record(db, _user_actor(initialized), action=AuditAction.WORK_ITEM_CREATE, resource_type="work_item")
    other = Actor(id="ghost", type=ActorType.USER, tenant_id="tenant-other")
    await service.record(db, other, action=AuditAction.WORK_ITEM_CREATE, resource_type="work_item")

    _, mine = await _page(db, initialized)
    assert mine == baseline + 1


async def test_ai_chain_by_resource_filter(db: AsyncSession, initialized: SimpleNamespace) -> None:
    aa = "agent-action-1"
    await service.record(
        db,
        _agent_actor(initialized),
        action=AuditAction.AI_PROPOSED_ACTION_CREATE,
        resource_type="agent_action",
        resource_id=aa,
    )
    await service.record(
        db,
        _user_actor(initialized),
        action=AuditAction.AGENT_ACTION_APPROVE,
        resource_type="agent_action",
        resource_id=aa,
    )
    await service.record(
        db,
        _agent_actor(initialized),
        action=AuditAction.AGENT_ACTION_EXECUTE,
        resource_type="agent_action",
        resource_id=aa,
    )

    items, total = await _page(db, initialized, resource_type="agent_action", resource_id=aa)
    assert total == 3
    chain = {i.action: i.actor.type for i in items}
    assert chain[AuditAction.AI_PROPOSED_ACTION_CREATE] == AuditActorType.AI_AGENT
    assert chain[AuditAction.AGENT_ACTION_APPROVE] == AuditActorType.USER
    assert chain[AuditAction.AGENT_ACTION_EXECUTE] == AuditActorType.AI_AGENT
