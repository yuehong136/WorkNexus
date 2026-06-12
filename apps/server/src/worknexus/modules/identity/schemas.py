from enum import StrEnum

from pydantic import EmailStr

from worknexus.core.access import Permission, Role
from worknexus.core.schemas import ApiModel


class UserStatus(StrEnum):
    ACTIVE = "active"
    INVITED = "invited"
    DISABLED = "disabled"


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
