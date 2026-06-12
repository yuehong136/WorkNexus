"""RBAC: 6 system roles x permission matrix (D3) and the single check entry point.

v0.1 deliberately has no roles/permissions tables — this module is the single
source of truth, and `can()` / `require_permission` are the only places where
permissions are evaluated. Matrix details and rationale: docs/modules/identity.md §6.
"""

from collections.abc import Callable, Coroutine, Iterable
from enum import StrEnum
from typing import Annotated, Any

from fastapi import Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.deps import Actor, ActorType, get_current_actor
from worknexus.core.errors import BizError, ErrorCode
from worknexus.db import get_db


class Role(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    PROJECT_ADMIN = "project_admin"
    MEMBER = "member"
    VIEWER = "viewer"
    AI_AGENT = "ai_agent"


TENANT_ROLES = frozenset({Role.OWNER, Role.ADMIN, Role.AI_AGENT})
PROJECT_ROLES = frozenset({Role.PROJECT_ADMIN, Role.MEMBER, Role.VIEWER})


class ScopeType(StrEnum):
    TENANT = "tenant"
    PROJECT = "project"


class SubjectType(StrEnum):
    USER = "user"
    AI_AGENT = "ai_agent"


class Permission(StrEnum):
    TENANT_MANAGE = "tenant.manage"
    USER_READ = "user.read"
    USER_INVITE = "user.invite"
    USER_MANAGE = "user.manage"
    ROLE_ASSIGN = "role.assign"
    AI_AGENT_READ = "ai_agent.read"
    AI_AGENT_MANAGE = "ai_agent.manage"
    AUDIT_READ = "audit.read"
    PROJECT_CREATE = "project.create"
    PROJECT_READ = "project.read"
    PROJECT_UPDATE = "project.update"
    PROJECT_ARCHIVE = "project.archive"
    PROJECT_MEMBER_MANAGE = "project.member.manage"
    WORK_ITEM_READ = "work_item.read"
    WORK_ITEM_CREATE = "work_item.create"
    WORK_ITEM_UPDATE = "work_item.update"
    WORK_ITEM_DELETE = "work_item.delete"
    WORK_ITEM_TRANSITION = "work_item.transition"
    WORK_ITEM_COMMENT = "work_item.comment"
    WORK_ITEM_ASSIGN = "work_item.assign"
    SKILL_READ = "skill.read"
    SKILL_INVOKE = "skill.invoke"
    WORKCHAT_USE = "workchat.use"
    AGENT_ACTION_CONFIRM = "agent_action.confirm"
    INTAKE_READ = "intake.read"
    INTAKE_CREATE = "intake.create"
    INTAKE_TRIAGE = "intake.triage"
    DASHBOARD_READ = "dashboard.read"


_VIEWER_PERMISSIONS = frozenset(
    {
        Permission.USER_READ,
        Permission.AI_AGENT_READ,
        Permission.PROJECT_READ,
        Permission.WORK_ITEM_READ,
        Permission.SKILL_READ,
        Permission.INTAKE_READ,
        Permission.DASHBOARD_READ,
    }
)

_MEMBER_PERMISSIONS = _VIEWER_PERMISSIONS | frozenset(
    {
        Permission.WORK_ITEM_CREATE,
        Permission.WORK_ITEM_UPDATE,
        Permission.WORK_ITEM_TRANSITION,
        Permission.WORK_ITEM_COMMENT,
        Permission.WORK_ITEM_ASSIGN,
        Permission.WORKCHAT_USE,
        Permission.AGENT_ACTION_CONFIRM,
        Permission.INTAKE_CREATE,
    }
)

_PROJECT_ADMIN_PERMISSIONS = _MEMBER_PERMISSIONS | frozenset(
    {
        Permission.PROJECT_UPDATE,
        Permission.PROJECT_ARCHIVE,
        Permission.PROJECT_MEMBER_MANAGE,
        Permission.WORK_ITEM_DELETE,
        Permission.INTAKE_TRIAGE,
    }
)

_ADMIN_PERMISSIONS = _PROJECT_ADMIN_PERMISSIONS | frozenset(
    {
        Permission.USER_INVITE,
        Permission.USER_MANAGE,
        Permission.ROLE_ASSIGN,
        Permission.AI_AGENT_MANAGE,
        Permission.AUDIT_READ,
        Permission.PROJECT_CREATE,
    }
)

# AI caps only: every write still passes the D5 double-check
# (user ∧ agent ∧ resource ∧ risk ∧ confirmation); high_write is never granted.
_AI_AGENT_PERMISSIONS = frozenset(
    {
        Permission.PROJECT_READ,
        Permission.WORK_ITEM_READ,
        Permission.WORK_ITEM_CREATE,
        Permission.WORK_ITEM_UPDATE,
        Permission.WORK_ITEM_TRANSITION,
        Permission.WORK_ITEM_COMMENT,
        Permission.WORK_ITEM_ASSIGN,
        Permission.SKILL_INVOKE,
        Permission.INTAKE_READ,
        Permission.INTAKE_CREATE,
        Permission.INTAKE_TRIAGE,
        Permission.DASHBOARD_READ,
    }
)

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.OWNER: _ADMIN_PERMISSIONS | {Permission.TENANT_MANAGE},
    Role.ADMIN: _ADMIN_PERMISSIONS,
    Role.PROJECT_ADMIN: _PROJECT_ADMIN_PERMISSIONS,
    Role.MEMBER: _MEMBER_PERMISSIONS,
    Role.VIEWER: _VIEWER_PERMISSIONS,
    Role.AI_AGENT: _AI_AGENT_PERMISSIONS,
}


def union_permissions(roles: Iterable[Role]) -> frozenset[Permission]:
    return frozenset[Permission]().union(*(ROLE_PERMISSIONS[r] for r in roles))


class Scope(BaseModel):
    type: ScopeType = ScopeType.TENANT
    project_id: str | None = None


class Subject(BaseModel):
    """An actor plus its resolved roles — loaded once per request."""

    actor: Actor
    tenant_roles: list[Role] = Field(default_factory=list)
    project_roles: dict[str, Role] = Field(default_factory=dict)


async def load_subject(db: AsyncSession, actor: Actor) -> Subject:
    # Read-only lookups against identity tables; writes stay in identity.service.
    from worknexus.modules.identity.models import ProjectMember, RoleBinding

    subject_type = SubjectType.AI_AGENT if actor.type == ActorType.AI_AGENT else SubjectType.USER
    bindings = await db.execute(
        select(RoleBinding.role, RoleBinding.scope_type, RoleBinding.scope_id).where(
            RoleBinding.subject_type == subject_type, RoleBinding.subject_id == actor.id
        )
    )
    tenant_roles: set[Role] = set()
    project_roles: dict[str, Role] = {}
    for role, scope_type, scope_id in bindings.all():
        if scope_type == ScopeType.TENANT:
            tenant_roles.add(Role(role))
        elif scope_id is not None:
            project_roles[scope_id] = Role(role)
    if subject_type == SubjectType.USER:
        memberships = await db.execute(
            select(ProjectMember.project_id, ProjectMember.role).where(ProjectMember.user_id == actor.id)
        )
        for project_id, role in memberships.all():
            project_roles[project_id] = Role(role)
    return Subject(actor=actor, tenant_roles=sorted(tenant_roles, key=list(Role).index), project_roles=project_roles)


def permissions_for(subject: Subject, project_id: str | None = None) -> frozenset[Permission]:
    """Effective permissions. Tenant roles apply globally. Without a project_id this
    is the cross-role union (tenant-level capability checks like user.read); with one,
    only that project's role contributes on top of the tenant roles."""
    permissions = union_permissions(subject.tenant_roles)
    if project_id is None:
        permissions |= union_permissions(subject.project_roles.values())
    else:
        role = subject.project_roles.get(project_id)
        if role is not None:
            permissions |= ROLE_PERMISSIONS[role]
    return permissions


def can(subject: Subject, action: Permission, scope: Scope | None = None) -> bool:
    if scope is not None and scope.type == ScopeType.PROJECT:
        if scope.project_id is None:
            return False
        return action in permissions_for(subject, scope.project_id)
    return action in permissions_for(subject)


async def get_current_subject(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    actor: Annotated[Actor, Depends(get_current_actor)],
) -> Subject:
    cached = getattr(request.state, "subject", None)
    if isinstance(cached, Subject):
        return cached
    subject = await load_subject(db, actor)
    request.state.subject = subject
    return subject


def require_permission(
    action: Permission, *, project_param: str | None = None
) -> Callable[..., Coroutine[Any, Any, Subject]]:
    """Dependency factory: resolves the Subject and enforces `action`.

    With project_param, the project id is taken from the path (or query) parameter
    of that name and the check runs project-scoped."""

    async def dependency(
        request: Request,
        subject: Annotated[Subject, Depends(get_current_subject)],
    ) -> Subject:
        scope: Scope | None = None
        if project_param is not None:
            raw = request.path_params.get(project_param) or request.query_params.get(project_param)
            scope = Scope(type=ScopeType.PROJECT, project_id=str(raw) if raw else None)
        if not can(subject, action, scope):
            raise BizError(ErrorCode.FORBIDDEN, "permission denied")
        return subject

    return dependency
