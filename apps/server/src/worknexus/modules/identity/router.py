from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.config import get_settings
from worknexus.core.access import Permission, Subject, require_permission
from worknexus.core.deps import Actor, get_current_actor
from worknexus.core.envelope import Envelope
from worknexus.core.pagination import Page, PageParamsDep
from worknexus.db import get_db
from worknexus.modules.identity import service
from worknexus.modules.identity.schemas import (
    AcceptInviteIn,
    CurrentUserContext,
    InviteCreatedOut,
    InviteCreateIn,
    InviteOut,
    InvitePreviewOut,
    LoginIn,
    ProfileUpdateIn,
    SetupIn,
    SetupStatusOut,
    UserListOut,
)

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


@router.get("/me", operation_id="get_me")
async def get_me(
    actor: Annotated[Actor, Depends(get_current_actor)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Envelope[CurrentUserContext]:
    user = await service.get_user(db, actor.id)
    return Envelope(data=await service.build_current_user_context(db, user))


@router.patch("/me", operation_id="update_me")
async def update_me(
    payload: ProfileUpdateIn,
    actor: Annotated[Actor, Depends(get_current_actor)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Envelope[CurrentUserContext]:
    return Envelope(data=await service.update_profile(db, actor, payload))


@router.get("/users", operation_id="list_users")
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    params: PageParamsDep,
    subject: Annotated[Subject, Depends(require_permission(Permission.USER_READ))],
) -> Envelope[Page[UserListOut]]:
    users, total = await service.list_users(db, subject.actor, params)
    items = [UserListOut.model_validate(u) for u in users]
    return Envelope(data=Page.build(items, total, params))


@router.post("/invites", operation_id="create_invite")
async def create_invite(
    payload: InviteCreateIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: Annotated[Subject, Depends(require_permission(Permission.USER_INVITE))],
) -> Envelope[InviteCreatedOut]:
    invite, token = await service.create_invite(db, subject.actor, payload)
    return Envelope(data=InviteCreatedOut(invite=invite, token=token))


@router.get("/invites", operation_id="list_invites")
async def list_invites(
    db: Annotated[AsyncSession, Depends(get_db)],
    params: PageParamsDep,
    subject: Annotated[Subject, Depends(require_permission(Permission.USER_INVITE))],
) -> Envelope[Page[InviteOut]]:
    invites, total = await service.list_invites(db, subject.actor, params)
    return Envelope(data=Page.build(invites, total, params))


@router.post("/invites/{invite_id}/revoke", operation_id="revoke_invite")
async def revoke_invite(
    invite_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    subject: Annotated[Subject, Depends(require_permission(Permission.USER_INVITE))],
) -> Envelope[InviteOut]:
    return Envelope(data=await service.revoke_invite(db, subject.actor, invite_id))


@router.get("/invites/{token}", operation_id="get_invite")
async def get_invite(
    token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Envelope[InvitePreviewOut]:
    return Envelope(data=await service.get_invite_preview(db, token))


@router.post("/invites/{token}/accept", operation_id="accept_invite")
async def accept_invite(
    token: str,
    payload: AcceptInviteIn,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Envelope[CurrentUserContext]:
    user, issued = await service.accept_invite(
        db, token, payload, ip_address=_client_ip(request), user_agent=request.headers.get("user-agent")
    )
    _set_session_cookie(response, issued.token)
    return Envelope(data=await service.build_current_user_context(db, user))
