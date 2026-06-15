from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.access import Subject, get_current_subject
from worknexus.core.envelope import Envelope
from worknexus.db import get_db
from worknexus.modules.home import service
from worknexus.modules.home.schemas import HomeSnapshotOut

router = APIRouter(tags=["home"])


@router.get("/home", operation_id="get_home")
async def get_home(
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: Annotated[Subject, Depends(get_current_subject)],
) -> Envelope[HomeSnapshotOut]:
    return Envelope(data=await service.get_home_snapshot(db, subject))
