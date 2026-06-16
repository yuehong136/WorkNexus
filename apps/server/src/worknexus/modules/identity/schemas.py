from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, EmailStr, Field

from worknexus.core.access import Permission, Role
from worknexus.core.schemas import ApiModel


class UserStatus(StrEnum):
    ACTIVE = "active"
    INVITED = "invited"
    DISABLED = "disabled"


class InviteStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


class IdentityProvider(StrEnum):
    LOCAL = "local"
    MULTIRAG = "multirag"
    OIDC = "oidc"


class AgentStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class SetupStatusOut(ApiModel):
    initialized: bool


class SetupIn(ApiModel):
    workspace_name: str = "Default Workspace"
    email: EmailStr
    display_name: str
    password: str


class LoginIn(ApiModel):
    email: EmailStr
    password: str


class ProfileUpdateIn(ApiModel):
    """Settings Lite: the only self-editable profile field in v0.1 (password/avatar deferred)."""

    display_name: str = Field(min_length=1, max_length=100)


class UserOut(ApiModel):
    id: str
    email: str
    display_name: str
    avatar_url: str | None
    identity_provider: IdentityProvider
    external_user_id: str | None


class TenantOut(ApiModel):
    id: str
    name: str
    slug: str


class ProjectAccessOut(ApiModel):
    id: str
    name: str
    role: Role
    permissions: list[Permission]


class AgentOut(ApiModel):
    id: str
    name: str
    status: AgentStatus


class AIContextOut(ApiModel):
    available_agents: list[AgentOut]


class CurrentUserContext(ApiModel):
    user: UserOut
    tenant: TenantOut
    roles: list[Role]
    permissions: list[Permission]
    projects: list[ProjectAccessOut]
    ai: AIContextOut


class UserListOut(UserOut):
    status: UserStatus
    last_login_at: datetime | None
    created_at: datetime


class InviteCreateIn(ApiModel):
    email: EmailStr
    tenant_role: Role | None = None
    project_id: str | None = None
    project_role: Role | None = None


class InviteOut(ApiModel):
    id: str
    email: str
    status: InviteStatus
    tenant_role: Role | None
    project_id: str | None
    project_role: Role | None
    expires_at: datetime
    created_at: datetime


class InviteCreatedOut(ApiModel):
    invite: InviteOut
    # Plaintext invite token — returned only from this response, never stored.
    token: str


class InvitePreviewOut(ApiModel):
    email: str
    status: InviteStatus
    tenant_role: Role | None
    project_id: str | None
    project_name: str | None
    project_role: Role | None


class AcceptInviteIn(ApiModel):
    display_name: str
    password: str


class IssuedDelegationToken(BaseModel):
    token: str
    expires_at: datetime


class DelegationContext(BaseModel):
    tenant_id: str
    user_id: str
    agent_id: str
    project_id: str | None
    conversation_id: str | None
    run_id: str | None
    permissions_snapshot: dict[str, Any]
