from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.envelope import ok
from worknexus.db import get_db

router = APIRouter(tags=["system"])


@router.get("/health", operation_id="get_health")
async def get_health(db: Annotated[AsyncSession, Depends(get_db)]) -> dict[str, Any]:
    try:
        await db.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "unavailable"
    return ok({"status": "ok", "database": database})
