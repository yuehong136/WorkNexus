"""RBAC constants: 6 system roles x permission matrix (decision D3).

v0.1 deliberately has no roles/permissions tables — this module is the single
source of truth. `can()` / `require_permission` land here in the next PR.
Matrix details and rationale: docs/modules/identity.md §6.
"""

from enum import StrEnum


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
