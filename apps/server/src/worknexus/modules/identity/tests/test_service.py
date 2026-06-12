"""Service-level identity tests against real PostgreSQL (rollback fixture)."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.deps import ActorType
from worknexus.core.errors import BizError, ErrorCode
from worknexus.modules.audit.models import AuditLog
from worknexus.modules.audit.service import AuditAction
from worknexus.modules.identity import service
from worknexus.modules.identity.models import ProjectMember, RoleBinding, Session, User

pytestmark = pytest.mark.integration


@pytest.mark.p0
async def test_setup_seeds_bindings_without_project_members(db: AsyncSession, initialized: SimpleNamespace) -> None:
    bindings = (await db.execute(select(RoleBinding))).scalars().all()
    by_subject = {(b.subject_type, b.role) for b in bindings}
    assert by_subject == {("user", "owner"), ("ai_agent", "ai_agent")}
    # Tenant roles are global: setup must not create project_members rows (D3).
    assert (await db.execute(select(ProjectMember))).first() is None


@pytest.mark.p1
async def test_setup_and_login_write_audit_rows(db: AsyncSession, initialized: SimpleNamespace) -> None:
    await service.login(
        db, email="owner@example.com", password="owner-pass-123", ip_address="127.0.0.1", user_agent="pytest"
    )
    actions = (await db.execute(select(AuditLog.action).order_by(AuditLog.created_at))).scalars().all()
    assert AuditAction.SETUP_COMPLETE in actions
    assert AuditAction.AUTH_LOGIN in actions


@pytest.mark.p1
async def test_session_token_stored_hashed(db: AsyncSession, initialized: SimpleNamespace) -> None:
    session = (await db.execute(select(Session))).scalar_one()
    assert session.token_hash != initialized.session.token
    assert session.token_hash == service.hash_token(initialized.session.token)
    assert initialized.session.token.startswith("wn_sess_")


@pytest.mark.p0
async def test_resolve_session_actor_valid(db: AsyncSession, initialized: SimpleNamespace) -> None:
    actor = await service.resolve_session_actor(db, initialized.session.token)
    assert actor.id == initialized.owner.id
    assert actor.type == ActorType.USER
    assert actor.tenant_id == initialized.tenant.id


@pytest.mark.p1
async def test_resolve_session_actor_rejects_garbage(db: AsyncSession, initialized: SimpleNamespace) -> None:
    with pytest.raises(BizError) as excinfo:
        await service.resolve_session_actor(db, "wn_sess_not-a-real-token")
    assert excinfo.value.code == ErrorCode.UNAUTHORIZED


@pytest.mark.p1
async def test_resolve_session_actor_rejects_expired(db: AsyncSession, initialized: SimpleNamespace) -> None:
    session = (await db.execute(select(Session))).scalar_one()
    session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db.flush()
    with pytest.raises(BizError) as excinfo:
        await service.resolve_session_actor(db, initialized.session.token)
    assert excinfo.value.code == ErrorCode.UNAUTHORIZED


@pytest.mark.p1
async def test_resolve_session_actor_rejects_disabled_user(db: AsyncSession, initialized: SimpleNamespace) -> None:
    initialized.owner.status = "disabled"
    await db.flush()
    with pytest.raises(BizError):
        await service.resolve_session_actor(db, initialized.session.token)


@pytest.mark.p2
async def test_last_seen_write_is_throttled(db: AsyncSession, initialized: SimpleNamespace) -> None:
    await service.resolve_session_actor(db, initialized.session.token)
    session = (await db.execute(select(Session))).scalar_one()
    first_seen = session.last_seen_at
    assert first_seen is not None
    await service.resolve_session_actor(db, initialized.session.token)
    assert session.last_seen_at == first_seen


@pytest.mark.p1
async def test_current_user_context_for_project_member(
    db: AsyncSession, initialized: SimpleNamespace, member_user: User
) -> None:
    db.add(
        ProjectMember(
            tenant_id=initialized.tenant.id,
            project_id=initialized.project.id,
            user_id=member_user.id,
            role="member",
            created_by=initialized.owner.id,
        )
    )
    await db.flush()
    ctx = await service.build_current_user_context(db, member_user)
    assert ctx.roles == []
    assert len(ctx.projects) == 1
    assert ctx.projects[0].role == "member"
    assert "work_item.create" in ctx.projects[0].permissions
    assert "work_item.delete" not in ctx.projects[0].permissions
    assert "user.read" in ctx.permissions


@pytest.mark.p1
async def test_audit_record_does_not_commit(db: AsyncSession, initialized: SimpleNamespace) -> None:
    from worknexus.core.deps import system_actor
    from worknexus.modules.audit import service as audit

    before = len((await db.execute(select(AuditLog))).scalars().all())
    await audit.record(
        db, system_actor(initialized.tenant.id), action="test.rollback", resource_type="tenant", resource_id="x"
    )
    await db.rollback()
    after = len((await db.execute(select(AuditLog))).scalars().all())
    assert after == before == 1  # only the committed setup.complete row survives
