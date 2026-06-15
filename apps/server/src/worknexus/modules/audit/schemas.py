from datetime import datetime
from enum import StrEnum
from typing import Any

from worknexus.core.schemas import ApiModel


class AuditActorType(StrEnum):
    USER = "user"
    AI_AGENT = "ai_agent"
    SYSTEM = "system"


class AuditActorOut(ApiModel):
    type: AuditActorType
    id: str | None
    display_name: str | None


class AuditLogOut(ApiModel):
    id: str
    created_at: datetime
    actor: AuditActorOut
    action: str
    resource_type: str
    resource_id: str | None
    project_id: str | None
    project_name: str | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    detail: dict[str, Any] | None
    request_id: str | None
    ip_address: str | None
