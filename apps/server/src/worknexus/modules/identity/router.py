from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.config import get_settings
from worknexus.core.deps import Actor, get_current_actor
from worknexus.core.envelope import Envelope
from worknexus.db import get_db
from worknexus.modules.identity import service
from worknexus.modules.identity.schemas import CurrentUserContext, LoginIn, SetupIn, SetupStatusOut

router = APIRouter(tags=["identity"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_days * 86400,
        httponly=True,
        samesite="lax",
        secure=settings.environment == "production",
        path="/",
    )


@router.get("/setup/status", operation_id="get_setup_status")
async def get_setup_status(db: Annotated[AsyncSession, Depends(get_db)]) -> Envelope[SetupStatusOut]:
    return Envelope(data=SetupStatusOut(initialized=await service.is_initialized(db)))


@router.post("/setup", operation_id="run_setup")
async def run_setup(
    payload: SetupIn,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Envelope[CurrentUserContext]:
    user, issued = await service.run_setup(
        db, payload, ip_address=_client_ip(request), user_agent=request.headers.get("user-agent")
    )
    _set_session_cookie(response, issued.token)
    return Envelope(data=await service.build_current_user_context(db, user))


@router.post("/auth/login", operation_id="login")
async def login(
    payload: LoginIn,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Envelope[CurrentUserContext]:
    user, issued = await service.login(
        db,
        email=str(payload.email),
        password=payload.password,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    _set_session_cookie(response, issued.token)
    return Envelope(data=await service.build_current_user_context(db, user))


@router.post("/auth/logout", operation_id="logout")
async def logout(
    request: Request,
    response: Response,
    actor: Annotated[Actor, Depends(get_current_actor)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Envelope[None]:
    token = request.cookies.get(get_settings().session_cookie_name)
    if token:
        await service.logout(db, actor, token=token)
    response.delete_cookie(get_settings().session_cookie_name, path="/")
    return Envelope()
