"""Pure truth-table checks of the role x permission matrix (docs/modules/identity.md §6)."""

import pytest

from worknexus.core.access import ROLE_PERMISSIONS, Permission, Role

pytestmark = pytest.mark.p0

HIGH_WRITE_PERMISSIONS = {
    Permission.TENANT_MANAGE,
    Permission.USER_MANAGE,
    Permission.ROLE_ASSIGN,
    Permission.AI_AGENT_MANAGE,
    Permission.PROJECT_ARCHIVE,
    Permission.PROJECT_MEMBER_MANAGE,
    Permission.WORK_ITEM_DELETE,
}


def test_every_role_has_permissions_defined() -> None:
    assert set(ROLE_PERMISSIONS) == set(Role)


def test_owner_is_admin_plus_tenant_manage() -> None:
    assert ROLE_PERMISSIONS[Role.OWNER] - ROLE_PERMISSIONS[Role.ADMIN] == {Permission.TENANT_MANAGE}


def test_role_hierarchy_is_strictly_increasing() -> None:
    assert ROLE_PERMISSIONS[Role.VIEWER] < ROLE_PERMISSIONS[Role.MEMBER]
    assert ROLE_PERMISSIONS[Role.MEMBER] < ROLE_PERMISSIONS[Role.PROJECT_ADMIN]
    assert ROLE_PERMISSIONS[Role.PROJECT_ADMIN] < ROLE_PERMISSIONS[Role.ADMIN]
    assert ROLE_PERMISSIONS[Role.ADMIN] < ROLE_PERMISSIONS[Role.OWNER]


def test_viewer_is_read_only() -> None:
    viewer = ROLE_PERMISSIONS[Role.VIEWER]
    assert Permission.WORK_ITEM_READ in viewer
    assert Permission.WORK_ITEM_CREATE not in viewer
    assert Permission.WORKCHAT_USE not in viewer
    assert Permission.INTAKE_CREATE not in viewer


def test_member_cannot_delete_or_manage() -> None:
    member = ROLE_PERMISSIONS[Role.MEMBER]
    assert Permission.WORK_ITEM_CREATE in member
    assert Permission.WORK_ITEM_TRANSITION in member
    assert Permission.AGENT_ACTION_CONFIRM in member
    assert Permission.WORK_ITEM_DELETE not in member
    assert Permission.USER_INVITE not in member
    assert Permission.PROJECT_MEMBER_MANAGE not in member


def test_project_admin_scope() -> None:
    project_admin = ROLE_PERMISSIONS[Role.PROJECT_ADMIN]
    assert Permission.PROJECT_MEMBER_MANAGE in project_admin
    assert Permission.WORK_ITEM_DELETE in project_admin
    assert Permission.INTAKE_TRIAGE in project_admin
    assert Permission.USER_INVITE not in project_admin
    assert Permission.AUDIT_READ not in project_admin
    assert Permission.PROJECT_CREATE not in project_admin


def test_only_admin_roles_invite_and_audit() -> None:
    for role in (Role.OWNER, Role.ADMIN):
        assert Permission.USER_INVITE in ROLE_PERMISSIONS[role]
        assert Permission.AUDIT_READ in ROLE_PERMISSIONS[role]
        assert Permission.PROJECT_CREATE in ROLE_PERMISSIONS[role]


def test_ai_agent_caps_exclude_high_write() -> None:
    ai = ROLE_PERMISSIONS[Role.AI_AGENT]
    assert Permission.SKILL_INVOKE in ai
    assert Permission.WORK_ITEM_CREATE in ai
    assert Permission.INTAKE_TRIAGE in ai
    assert not ai & HIGH_WRITE_PERMISSIONS


def test_skill_invoke_is_ai_only() -> None:
    for role in set(Role) - {Role.AI_AGENT}:
        assert Permission.SKILL_INVOKE not in ROLE_PERMISSIONS[role]
