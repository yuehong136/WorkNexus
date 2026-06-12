import asyncio
import hashlib
import secrets
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import NamedTuple

import bcrypt
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.config import get_settings
from worknexus.core.access import ROLE_PERMISSIONS, Permission, Role, ScopeType, SubjectType
from worknexus.core.deps import Actor, ActorType, system_actor
from worknexus.core.errors import BizError, ErrorCode
from worknexus.modules.audit import service as audit
from worknexus.modules.audit.service import AuditAction
from worknexus.modules.identity.models import AIAgent, ProjectMember, RoleBinding, Session, Tenant, User
from worknexus.modules.identity.schemas import (
    AgentOut,
    AgentStatus,
    AIContextOut,
    CurrentUserContext,
    ProjectAccessOut,
    SetupIn,
    TenantOut,
    UserOut,
    UserStatus,
)
from worknexus.modules.projects import service as projects_service
from worknexus.modules.projects.models import Project

SETUP_LOCK_KEY = 746_199_101
PASSWORD_MIN_LENGTH = 8
SESSION_TOKEN_PREFIX = "wn_sess_"
LAST_SEEN_WRITE_INTERVAL = timedelta(minutes=5)


class IssuedSession(NamedTuple):
    token: str
    expires_at: datetime


def _now() -> datetime:
    return datetime.now(UTC)


def _union_permissions(roles: Iterable[Role]) -> frozenset[Permission]:
    return frozenset[Permission]().union(*(ROLE_PERMISSIONS[r] for r in roles))


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=get_settings().bcrypt_rounds)
    return (await asyncio.to_thread(bcrypt.hashpw, password.encode(), salt)).decode()


async def verify_password(password: str, password_hash: str) -> bool:
    return await asyncio.to_thread(bcrypt.checkpw, password.encode(), password_hash.encode())


def _validate_password(password: str) -> None:
    if len(password) < PASSWORD_MIN_LENGTH:
        raise BizError(ErrorCode.PASSWORD_TOO_WEAK, f"password must be at least {PASSWORD_MIN_LENGTH} characters")


async def _create_session(
    db: AsyncSession, user: User, *, ip_address: str | None, user_agent: str | None
) -> IssuedSession:
    token = SESSION_TOKEN_PREFIX + secrets.token_urlsafe(32)
    expires_at = _now() + timedelta(days=get_settings().session_ttl_days)
    db.add(
        Session(
            tenant_id=user.tenant_id,
            user_id=user.id,
            token_hash=hash_token(token),
            ip_address=ip_address,
            user_agent=user_agent[:400] if user_agent else None,
            expires_at=expires_at,
        )
    )
    await db.flush()
    return IssuedSession(token=token, expires_at=expires_at)


async def is_initialized(db: AsyncSession) -> bool:
    return (await db.execute(select(Tenant.id).limit(1))).first() is not None


async def run_setup(
    db: AsyncSession, data: SetupIn, *, ip_address: str | None, user_agent: str | None
) -> tuple[User, IssuedSession]:
    _validate_password(data.password)
    await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": SETUP_LOCK_KEY})
    if await is_initialized(db):
        raise BizError(ErrorCode.SETUP_ALREADY_COMPLETED, "setup already completed")

    settings = get_settings()
    tenant = Tenant(name=data.workspace_name, slug="default")
    db.add(tenant)
    await db.flush()

    owner = User(
        tenant_id=tenant.id,
        email=str(data.email).lower(),
        display_name=data.display_name,
        password_hash=await hash_password(data.password),
        identity_provider="local",
        status=UserStatus.ACTIVE,
    )
    db.add(owner)
    await db.flush()
    db.add(
        RoleBinding(
            tenant_id=tenant.id,
            subject_type=SubjectType.USER,
            subject_id=owner.id,
            role=Role.OWNER,
            scope_type=ScopeType.TENANT,
        )
    )

    owner_actor = Actor(id=owner.id, type=ActorType.USER, tenant_id=tenant.id)
    project = await projects_service.create_project(
        db, owner_actor, tenant_id=tenant.id, name="WorkNexus Internal", key="WNX", owner_id=owner.id
    )

    agent = AIAgent(
        tenant_id=tenant.id,
        name="WorkNexus Assistant",
        status=AgentStatus.ACTIVE,
        external_agent_id=settings.ai_platform_default_agent_id or None,
        created_by=owner.id,
    )
    db.add(agent)
    await db.flush()
    db.add(
        RoleBinding(
            tenant_id=tenant.id,
            subject_type=SubjectType.AI_AGENT,
            subject_id=agent.id,
            role=Role.AI_AGENT,
            scope_type=ScopeType.TENANT,
        )
    )

    await audit.record(
        db,
        system_actor(tenant.id),
        action=AuditAction.SETUP_COMPLETE,
        resource_type="tenant",
        resource_id=tenant.id,
        after={"owner_id": owner.id, "project_id": project.id, "agent_id": agent.id},
        ip_address=ip_address,
    )
    issued = await _create_session(db, owner, ip_address=ip_address, user_agent=user_agent)
    await db.commit()
    return owner, issued


async def login(
    db: AsyncSession, *, email: str, password: str, ip_address: str | None, user_agent: str | None
) -> tuple[User, IssuedSession]:
    user = (await db.execute(select(User).where(User.email == email.lower()))).scalar_one_or_none()
    if user is None or not user.password_hash or not await verify_password(password, user.password_hash):
        raise BizError(ErrorCode.INVALID_CREDENTIALS, "invalid email or password")
    if user.status != UserStatus.ACTIVE:
        raise BizError(ErrorCode.USER_DISABLED, "user is disabled")

    issued = await _create_session(db, user, ip_address=ip_address, user_agent=user_agent)
    user.last_login_at = _now()
    actor = Actor(id=user.id, type=ActorType.USER, tenant_id=user.tenant_id)
    await audit.record(
        db, actor, action=AuditAction.AUTH_LOGIN, resource_type="user", resource_id=user.id, ip_address=ip_address
    )
    await db.commit()
    return user, issued


async def logout(db: AsyncSession, actor: Actor, *, token: str) -> None:
    session = (await db.execute(select(Session).where(Session.token_hash == hash_token(token)))).scalar_one_or_none()
    if session is not None and session.revoked_at is None:
        session.revoked_at = _now()
        await audit.record(db, actor, action=AuditAction.AUTH_LOGOUT, resource_type="user", resource_id=actor.id)
        await db.commit()


async def resolve_session_actor(db: AsyncSession, token: str) -> Actor:
    now = _now()
    row = (
        await db.execute(
            select(Session, User).join(User, Session.user_id == User.id).where(Session.token_hash == hash_token(token))
        )
    ).first()
    if row is None:
        raise BizError(ErrorCode.UNAUTHORIZED, "not authenticated")
    session, user = row._tuple()
    if session.revoked_at is not None or session.expires_at <= now or user.status != UserStatus.ACTIVE:
        raise BizError(ErrorCode.UNAUTHORIZED, "not authenticated")
    if session.last_seen_at is None or now - session.last_seen_at > LAST_SEEN_WRITE_INTERVAL:
        session.last_seen_at = now
        await db.commit()
    return Actor(id=user.id, type=ActorType.USER, tenant_id=user.tenant_id)


async def get_user(db: AsyncSession, user_id: str) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise BizError(ErrorCode.NOT_FOUND, "user not found")
    return user


async def build_current_user_context(db: AsyncSession, user: User) -> CurrentUserContext:
    tenant = await db.get(Tenant, user.tenant_id)
    assert tenant is not None

    bindings = (
        await db.execute(
            select(RoleBinding.role).where(
                RoleBinding.subject_type == SubjectType.USER,
                RoleBinding.subject_id == user.id,
                RoleBinding.scope_type == ScopeType.TENANT,
            )
        )
    ).scalars()
    tenant_roles = sorted({Role(r) for r in bindings}, key=list(Role).index)
    tenant_permissions = _union_permissions(tenant_roles)

    memberships = (
        await db.execute(select(ProjectMember.project_id, ProjectMember.role).where(ProjectMember.user_id == user.id))
    ).all()
    project_roles = {project_id: Role(role) for project_id, role in memberships}

    # Top-level permissions are the union across all of the user's roles;
    # per-project enforcement always goes through projects[].permissions.
    all_permissions = tenant_permissions | _union_permissions(project_roles.values())

    projects: list[ProjectAccessOut] = []
    if tenant_roles:
        rows = (
            await db.execute(select(Project).where(Project.tenant_id == user.tenant_id, Project.status == "active"))
        ).scalars()
        projects = [
            ProjectAccessOut(id=p.id, name=p.name, role=tenant_roles[0], permissions=sorted(tenant_permissions))
            for p in rows
        ]
    else:
        for project_id, role in project_roles.items():
            project = await db.get(Project, project_id)
            if project is None or project.status != "active":
                continue
            permissions = sorted(tenant_permissions | ROLE_PERMISSIONS[role])
            projects.append(ProjectAccessOut(id=project.id, name=project.name, role=role, permissions=permissions))

    agents = (
        await db.execute(
            select(AIAgent).where(AIAgent.tenant_id == user.tenant_id, AIAgent.status == AgentStatus.ACTIVE)
        )
    ).scalars()

    return CurrentUserContext(
        user=UserOut.model_validate(user),
        tenant=TenantOut.model_validate(tenant),
        roles=tenant_roles,
        permissions=sorted(all_permissions),
        projects=projects,
        ai=AIContextOut(available_agents=[AgentOut.model_validate(a) for a in agents]),
    )
