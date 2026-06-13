import re
from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator

from worknexus.core.schemas import ApiModel

_KEY_PATTERN = re.compile(r"^[A-Z0-9]{2,10}$")


class ProjectStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class ProjectMemberRole(StrEnum):
    PROJECT_ADMIN = "project_admin"
    MEMBER = "member"
    VIEWER = "viewer"


class UserBriefOut(ApiModel):
    id: str
    display_name: str
    email: str
    avatar_url: str | None


class ProjectCreateIn(ApiModel):
    name: str = Field(min_length=1, max_length=200)
    key: str
    description: str | None = None

    @field_validator("key")
    @classmethod
    def _normalize_key(cls, value: str) -> str:
        key = value.strip().upper()
        if not _KEY_PATTERN.match(key):
            raise ValueError("key must be 2-10 uppercase letters or digits")
        return key


class ProjectUpdateIn(ApiModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class ProjectOut(ApiModel):
    id: str
    name: str
    key: str
    description: str | None
    status: ProjectStatus
    owner_id: str | None
    owner: UserBriefOut | None
    member_count: int
    created_at: datetime
    updated_at: datetime


class ProjectMemberAddIn(ApiModel):
    user_id: str
    role: ProjectMemberRole


class ProjectMemberUpdateIn(ApiModel):
    role: ProjectMemberRole


class ProjectMemberOut(ApiModel):
    user_id: str
    display_name: str
    email: str
    avatar_url: str | None
    role: ProjectMemberRole
    created_at: datetime
