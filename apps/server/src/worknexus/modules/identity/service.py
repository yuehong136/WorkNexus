import asyncio
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import NamedTuple

import bcrypt
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.config import get_settings
from worknexus.core.access import (
    PROJECT_ROLES,
    Role,
    ScopeType,
    SubjectType,
    load_subject,
    permissions_for,
    union_permissions,
)
from worknexus.core.deps import Actor, ActorType, system_actor
from worknexus.core.errors import BizError, ErrorCode
from worknexus.core.pagination import PageParams
from worknexus.modules.audit import service as audit
from worknexus.modules.audit.service import AuditAction
from worknexus.modules.identity.models import (
    AIAgent,
    InviteToken,
    McpDelegationToken,
    ProjectMember,
    RoleBinding,
    Session,
    Tenant,
    User,
)
from worknexus.modules.identity.schemas import (
    AcceptInviteIn,
    AgentOut,
    AgentStatus,
    AIContextOut,
    CurrentUserContext,
    DelegationContext,
    InviteCreateIn,
    InviteOut,
    InvitePreviewOut,
    InviteStatus,
    IssuedDelegationToken,
    ProfileUpdateIn,
    ProjectAccessOut,
    SetupIn,
    TenantOut,
    UserOut,
    UserStatus,
)
from worknexus.modules.projects import service as projects_service
from worknexus.modules.projects.models import Project
from worknexus.modules.projects.schemas import ProjectMemberOut, ProjectMemberRole

SETUP_LOCK_KEY = 746_199_101
PASSWORD_MIN_LENGTH = 8
SESSION_TOKEN_PREFIX = "wn_sess_"
INVITE_TOKEN_PREFIX = "wn_inv_"
DELEGATION_TOKEN_PREFIX = "wn_del_"
LAST_SEEN_WRITE_INTERVAL = timedelta(minutes=5)


class IssuedSession(NamedTuple):
    token: str
    expires_at: datetime


def _now() -> datetime:
    return datetime.now(UTC)


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
    project = await projects_service.insert_project(
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


async def update_profile(db: AsyncSession, actor: Actor, data: ProfileUpdateIn) -> CurrentUserContext:
    """Settings Lite: the caller updates their own display name (the only writable field
    in v0.1). Audited; password/avatar are deferred to a later security PR."""
    user = await get_user(db, actor.id)
    before = {"displayName": user.display_name}
    user.display_name = data.display_name
    await audit.record(
        db,
        actor,
        action=AuditAction.USER_PROFILE_UPDATE,
        resource_type="user",
        resource_id=user.id,
        before=before,
        after={"displayName": user.display_name},
    )
    await db.commit()
    return await build_current_user_context(db, user)


async def build_current_user_context(db: AsyncSession, user: User) -> CurrentUserContext:
    tenant = await db.get(Tenant, user.tenant_id)
    assert tenant is not None

    subject = await load_subject(db, Actor(id=user.id, type=ActorType.USER, tenant_id=user.tenant_id))
    tenant_permissions = union_permissions(subject.tenant_roles)
    # Top-level permissions are the union across all of the user's roles;
    # per-project enforcement always goes through projects[].permissions.
    all_permissions = permissions_for(subject)

    projects: list[ProjectAccessOut] = []
    if subject.tenant_roles:
        rows = (
            await db.execute(select(Project).where(Project.tenant_id == user.tenant_id, Project.status == "active"))
        ).scalars()
        projects = [
            ProjectAccessOut(id=p.id, name=p.name, role=subject.tenant_roles[0], permissions=sorted(tenant_permissions))
            for p in rows
        ]
    else:
        for project_id, role in subject.project_roles.items():
            project = await db.get(Project, project_id)
            if project is None or project.status != "active":
                continue
            permissions = sorted(permissions_for(subject, project_id))
            projects.append(ProjectAccessOut(id=project.id, name=project.name, role=role, permissions=permissions))

    agents = (
        await db.execute(
            select(AIAgent).where(AIAgent.tenant_id == user.tenant_id, AIAgent.status == AgentStatus.ACTIVE)
        )
    ).scalars()

    return CurrentUserContext(
        user=UserOut.model_validate(user),
        tenant=TenantOut.model_validate(tenant),
        roles=subject.tenant_roles,
        permissions=sorted(all_permissions),
        projects=projects,
        ai=AIContextOut(available_agents=[AgentOut.model_validate(a) for a in agents]),
    )


async def list_users(db: AsyncSession, actor: Actor, params: PageParams) -> tuple[list[User], int]:
    base = select(User).where(User.tenant_id == actor.tenant_id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    users = (
        (await db.execute(base.order_by(User.created_at).offset(params.offset).limit(params.page_size))).scalars().all()
    )
    return list(users), total


def _invite_status(invite: InviteToken) -> InviteStatus:
    if invite.accepted_at is not None:
        return InviteStatus.ACCEPTED
    if invite.revoked_at is not None:
        return InviteStatus.REVOKED
    if invite.expires_at <= _now():
        return InviteStatus.EXPIRED
    return InviteStatus.PENDING


def _invite_out(invite: InviteToken) -> InviteOut:
    return InviteOut(
        id=invite.id,
        email=invite.email,
        status=_invite_status(invite),
        tenant_role=Role(invite.tenant_role) if invite.tenant_role else None,
        project_id=invite.project_id,
        project_role=Role(invite.project_role) if invite.project_role else None,
        expires_at=invite.expires_at,
        created_at=invite.created_at,
    )


def _validate_invite_target(data: InviteCreateIn) -> None:
    has_tenant_target = data.tenant_role is not None
    has_project_target = data.project_id is not None or data.project_role is not None
    if has_tenant_target == has_project_target:
        raise BizError(ErrorCode.INVALID_INPUT, "invite must target either a tenant role or a project role")
    if has_tenant_target and data.tenant_role != Role.ADMIN:
        raise BizError(ErrorCode.INVALID_INPUT, "only the admin tenant role can be granted via invite")
    if has_project_target:
        if data.project_id is None or data.project_role is None:
            raise BizError(ErrorCode.INVALID_INPUT, "project invites need both project id and project role")
        if data.project_role not in PROJECT_ROLES:
            raise BizError(ErrorCode.INVALID_INPUT, "invalid project role")


async def create_invite(db: AsyncSession, actor: Actor, data: InviteCreateIn) -> tuple[InviteOut, str]:
    _validate_invite_target(data)
    email = str(data.email).lower()
    existing_user = (
        await db.execute(select(User.id).where(User.tenant_id == actor.tenant_id, User.email == email))
    ).first()
    if existing_user is not None:
        raise BizError(ErrorCode.EMAIL_ALREADY_EXISTS, "a user with this email already exists")
    pending = (
        await db.execute(
            select(InviteToken.id).where(
                InviteToken.tenant_id == actor.tenant_id,
                InviteToken.email == email,
                InviteToken.accepted_at.is_(None),
                InviteToken.revoked_at.is_(None),
            )
        )
    ).first()
    if pending is not None:
        raise BizError(ErrorCode.EMAIL_ALREADY_EXISTS, "a pending invite for this email already exists")
    if data.project_id is not None:
        project = await db.get(Project, data.project_id)
        if project is None or project.tenant_id != actor.tenant_id or project.status != "active":
            raise BizError(ErrorCode.NOT_FOUND, "project not found")

    token = INVITE_TOKEN_PREFIX + secrets.token_urlsafe(32)
    invite = InviteToken(
        tenant_id=actor.tenant_id,
        token_hash=hash_token(token),
        email=email,
        created_by=actor.id,
        tenant_role=data.tenant_role,
        project_id=data.project_id,
        project_role=data.project_role,
        expires_at=_now() + timedelta(days=get_settings().invite_ttl_days),
    )
    db.add(invite)
    await db.flush()
    await audit.record(
        db,
        actor,
        action=AuditAction.INVITE_CREATE,
        resource_type="invite",
        resource_id=invite.id,
        project_id=data.project_id,
        after={"email": email, "tenant_role": data.tenant_role, "project_role": data.project_role},
    )
    await db.commit()
    return _invite_out(invite), token


async def list_invites(db: AsyncSession, actor: Actor, params: PageParams) -> tuple[list[InviteOut], int]:
    base = select(InviteToken).where(InviteToken.tenant_id == actor.tenant_id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    invites = (
        (await db.execute(base.order_by(InviteToken.created_at.desc()).offset(params.offset).limit(params.page_size)))
        .scalars()
        .all()
    )
    return [_invite_out(i) for i in invites], total


async def revoke_invite(db: AsyncSession, actor: Actor, invite_id: str) -> InviteOut:
    invite = await db.get(InviteToken, invite_id)
    if invite is None or invite.tenant_id != actor.tenant_id:
        raise BizError(ErrorCode.INVITE_NOT_FOUND, "invite not found")
    status = _invite_status(invite)
    if status == InviteStatus.ACCEPTED:
        raise BizError(ErrorCode.INVITE_ALREADY_ACCEPTED, "invite already accepted")
    if status == InviteStatus.REVOKED:
        raise BizError(ErrorCode.INVITE_REVOKED, "invite already revoked")
    invite.revoked_at = _now()
    await audit.record(
        db,
        actor,
        action=AuditAction.INVITE_REVOKE,
        resource_type="invite",
        resource_id=invite.id,
        project_id=invite.project_id,
        after={"email": invite.email},
    )
    await db.commit()
    return _invite_out(invite)


async def get_invite_preview(db: AsyncSession, token: str) -> InvitePreviewOut:
    invite = (
        await db.execute(select(InviteToken).where(InviteToken.token_hash == hash_token(token)))
    ).scalar_one_or_none()
    if invite is None:
        raise BizError(ErrorCode.INVITE_NOT_FOUND, "invite not found")
    project_name: str | None = None
    if invite.project_id is not None:
        project = await db.get(Project, invite.project_id)
        project_name = project.name if project else None
    return InvitePreviewOut(
        email=invite.email,
        status=_invite_status(invite),
        tenant_role=Role(invite.tenant_role) if invite.tenant_role else None,
        project_id=invite.project_id,
        project_name=project_name,
        project_role=Role(invite.project_role) if invite.project_role else None,
    )


def _ensure_invite_acceptable(invite: InviteToken) -> None:
    status = _invite_status(invite)
    if status == InviteStatus.ACCEPTED:
        raise BizError(ErrorCode.INVITE_ALREADY_ACCEPTED, "invite already accepted")
    if status == InviteStatus.REVOKED:
        raise BizError(ErrorCode.INVITE_REVOKED, "invite has been revoked")
    if status == InviteStatus.EXPIRED:
        raise BizError(ErrorCode.INVITE_EXPIRED, "invite has expired")


async def accept_invite(
    db: AsyncSession, token: str, data: AcceptInviteIn, *, ip_address: str | None, user_agent: str | None
) -> tuple[User, IssuedSession]:
    _validate_password(data.password)
    invite = (
        await db.execute(select(InviteToken).where(InviteToken.token_hash == hash_token(token)))
    ).scalar_one_or_none()
    if invite is None:
        raise BizError(ErrorCode.INVITE_NOT_FOUND, "invite not found")
    _ensure_invite_acceptable(invite)
    existing = (
        await db.execute(select(User.id).where(User.tenant_id == invite.tenant_id, User.email == invite.email))
    ).first()
    if existing is not None:
        raise BizError(ErrorCode.EMAIL_ALREADY_EXISTS, "a user with this email already exists")

    user = User(
        tenant_id=invite.tenant_id,
        email=invite.email,
        display_name=data.display_name,
        password_hash=await hash_password(data.password),
        identity_provider="local",
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    await db.flush()
    actor = Actor(id=user.id, type=ActorType.USER, tenant_id=user.tenant_id)

    # The invite target is XOR by CHECK constraint: tenant role binding or
    # project membership — never both (D3).
    if invite.tenant_role is not None:
        db.add(
            RoleBinding(
                tenant_id=invite.tenant_id,
                subject_type=SubjectType.USER,
                subject_id=user.id,
                role=invite.tenant_role,
                scope_type=ScopeType.TENANT,
                created_by=invite.created_by,
            )
        )
        await audit.record(
            db,
            actor,
            action=AuditAction.ROLE_BINDING_CREATE,
            resource_type="user",
            resource_id=user.id,
            after={"role": invite.tenant_role, "scope_type": ScopeType.TENANT},
        )
    else:
        assert invite.project_id is not None and invite.project_role is not None
        db.add(
            ProjectMember(
                tenant_id=invite.tenant_id,
                project_id=invite.project_id,
                user_id=user.id,
                role=invite.project_role,
                created_by=invite.created_by,
            )
        )
        await audit.record(
            db,
            actor,
            action=AuditAction.PROJECT_MEMBER_ADD,
            resource_type="user",
            resource_id=user.id,
            project_id=invite.project_id,
            after={"role": invite.project_role},
        )

    invite.accepted_at = _now()
    invite.accepted_user_id = user.id
    await audit.record(
        db,
        actor,
        action=AuditAction.INVITE_ACCEPT,
        resource_type="invite",
        resource_id=invite.id,
        project_id=invite.project_id,
        ip_address=ip_address,
    )
    issued = await _create_session(db, user, ip_address=ip_address, user_agent=user_agent)
    await db.commit()
    return user, issued


async def issue_delegation_token(
    db: AsyncSession,
    actor: Actor,
    *,
    user_id: str,
    agent_id: str,
    project_id: str | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
) -> IssuedDelegationToken:
    user = await db.get(User, user_id)
    if user is None or user.tenant_id != actor.tenant_id:
        raise BizError(ErrorCode.NOT_FOUND, "user not found")
    if user.status != UserStatus.ACTIVE:
        raise BizError(ErrorCode.USER_DISABLED, "user is disabled")
    agent = await db.get(AIAgent, agent_id)
    if agent is None or agent.tenant_id != actor.tenant_id or agent.status != AgentStatus.ACTIVE:
        raise BizError(ErrorCode.NOT_FOUND, "ai agent not found or disabled")

    user_subject = await load_subject(db, Actor(id=user.id, type=ActorType.USER, tenant_id=user.tenant_id))
    agent_subject = await load_subject(db, Actor(id=agent.id, type=ActorType.AI_AGENT, tenant_id=agent.tenant_id))
    user_permissions = permissions_for(user_subject, project_id)
    agent_permissions = permissions_for(agent_subject, project_id)

    token = DELEGATION_TOKEN_PREFIX + secrets.token_urlsafe(32)
    expires_at = _now() + timedelta(seconds=get_settings().delegation_token_ttl_seconds)
    db.add(
        McpDelegationToken(
            tenant_id=actor.tenant_id,
            token_hash=hash_token(token),
            user_id=user.id,
            agent_id=agent.id,
            project_id=project_id,
            conversation_id=conversation_id,
            run_id=run_id,
            permissions_snapshot={
                "user": sorted(user_permissions),
                "agent": sorted(agent_permissions),
                "effective": sorted(user_permissions & agent_permissions),
            },
            expires_at=expires_at,
        )
    )
    await db.commit()
    return IssuedDelegationToken(token=token, expires_at=expires_at)


async def verify_delegation_token(db: AsyncSession, token: str) -> DelegationContext:
    row = (
        await db.execute(select(McpDelegationToken).where(McpDelegationToken.token_hash == hash_token(token)))
    ).scalar_one_or_none()
    if row is None or row.revoked_at is not None:
        raise BizError(ErrorCode.DELEGATION_TOKEN_INVALID, "delegation token invalid")
    if row.expires_at <= _now():
        raise BizError(ErrorCode.DELEGATION_TOKEN_EXPIRED, "delegation token expired")
    row.last_used_at = _now()
    await db.commit()
    return DelegationContext(
        tenant_id=row.tenant_id,
        user_id=row.user_id,
        agent_id=row.agent_id,
        project_id=row.project_id,
        conversation_id=row.conversation_id,
        run_id=row.run_id,
        permissions_snapshot=row.permissions_snapshot,
    )


# Project membership lives in project_members (D3: identity owns this table). projects.router
# exposes the /projects/{id}/members endpoints and calls into these functions, so the only
# writes to project_members are here, alongside their audit rows.


def _member_out(member: ProjectMember, user: User) -> ProjectMemberOut:
    return ProjectMemberOut(
        user_id=user.id,
        display_name=user.display_name,
        email=user.email,
        avatar_url=user.avatar_url,
        role=ProjectMemberRole(member.role),
        created_at=member.created_at,
    )


async def _is_tenant_owner(db: AsyncSession, user_id: str) -> bool:
    row = (
        await db.execute(
            select(RoleBinding.id).where(
                RoleBinding.subject_type == SubjectType.USER,
                RoleBinding.subject_id == user_id,
                RoleBinding.role == Role.OWNER,
                RoleBinding.scope_type == ScopeType.TENANT,
            )
        )
    ).first()
    return row is not None


async def _get_membership(db: AsyncSession, project_id: str, user_id: str) -> ProjectMember | None:
    return (
        await db.execute(
            select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
        )
    ).scalar_one_or_none()


async def list_project_members(db: AsyncSession, actor: Actor, project_id: str) -> list[ProjectMemberOut]:
    await projects_service.get_project(db, project_id, actor.tenant_id)
    rows = (
        await db.execute(
            select(ProjectMember, User)
            .join(User, User.id == ProjectMember.user_id)
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.created_at)
        )
    ).all()
    return [_member_out(member, user) for member, user in rows]


async def add_project_member(
    db: AsyncSession, actor: Actor, project_id: str, user_id: str, role: ProjectMemberRole
) -> ProjectMemberOut:
    await projects_service.get_project(db, project_id, actor.tenant_id)
    user = await db.get(User, user_id)
    if user is None or user.tenant_id != actor.tenant_id:
        raise BizError(ErrorCode.NOT_FOUND, "user not found")
    if await _is_tenant_owner(db, user_id):
        raise BizError(ErrorCode.CANNOT_MANAGE_OWNER_MEMBERSHIP, "cannot manage the workspace owner's membership")
    if await _get_membership(db, project_id, user_id) is not None:
        raise BizError(ErrorCode.MEMBER_ALREADY_EXISTS, "user is already a project member")
    member = ProjectMember(
        tenant_id=actor.tenant_id,
        project_id=project_id,
        user_id=user_id,
        role=role,
        created_by=actor.id,
    )
    db.add(member)
    await db.flush()
    await audit.record(
        db,
        actor,
        action=AuditAction.PROJECT_MEMBER_ADD,
        resource_type="user",
        resource_id=user_id,
        project_id=project_id,
        after={"role": role},
    )
    await db.commit()
    return _member_out(member, user)


async def update_project_member_role(
    db: AsyncSession, actor: Actor, project_id: str, user_id: str, role: ProjectMemberRole
) -> ProjectMemberOut:
    await projects_service.get_project(db, project_id, actor.tenant_id)
    member = await _get_membership(db, project_id, user_id)
    if member is None:
        raise BizError(ErrorCode.MEMBER_NOT_FOUND, "user is not a project member")
    before = {"role": member.role}
    member.role = role
    await db.flush()
    await audit.record(
        db,
        actor,
        action=AuditAction.PROJECT_MEMBER_UPDATE,
        resource_type="user",
        resource_id=user_id,
        project_id=project_id,
        before=before,
        after={"role": role},
    )
    await db.commit()
    user = await db.get(User, user_id)
    assert user is not None
    return _member_out(member, user)


async def remove_project_member(db: AsyncSession, actor: Actor, project_id: str, user_id: str) -> None:
    await projects_service.get_project(db, project_id, actor.tenant_id)
    member = await _get_membership(db, project_id, user_id)
    if member is None:
        raise BizError(ErrorCode.MEMBER_NOT_FOUND, "user is not a project member")
    before = {"role": member.role}
    await db.delete(member)
    await db.flush()
    await audit.record(
        db,
        actor,
        action=AuditAction.PROJECT_MEMBER_REMOVE,
        resource_type="user",
        resource_id=user_id,
        project_id=project_id,
        before=before,
    )
    await db.commit()
