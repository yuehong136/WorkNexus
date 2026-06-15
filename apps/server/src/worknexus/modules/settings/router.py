from typing import Annotated

from fastapi import APIRouter, Depends

from worknexus.config import Settings, get_settings
from worknexus.core.access import Permission, Subject, require_permission
from worknexus.core.envelope import Envelope
from worknexus.modules.settings import service
from worknexus.modules.settings.schemas import AiConnectionOut

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/ai-connection", operation_id="get_ai_connection")
async def get_ai_connection(
    _: Annotated[Subject, Depends(require_permission(Permission.AI_AGENT_MANAGE))],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Envelope[AiConnectionOut]:
    return Envelope(data=service.get_ai_connection(settings))
