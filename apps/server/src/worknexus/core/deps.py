from enum import StrEnum

from pydantic import BaseModel


class ActorType(StrEnum):
    USER = "user"
    AI = "ai"
    SYSTEM = "system"


class Actor(BaseModel):
    id: str
    type: ActorType
    tenant_id: str = "default"


async def get_current_actor() -> Actor:
    # Auth stub until the users module lands; see docs/modules/scaffold.md.
    return Actor(id="dev-user", type=ActorType.USER)
