import logging
from enum import IntEnum

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class ErrorCode(IntEnum):
    # 1xxx: generic
    INTERNAL = 1000
    NOT_FOUND = 1001
    INVALID_INPUT = 1002
    UNAUTHORIZED = 1003
    FORBIDDEN = 1004
    # 2xxx: work_items
    WORK_ITEM_NOT_FOUND = 2001
    INVALID_STATUS_TRANSITION = 2002
    COMMENT_NOT_FOUND = 2003
    RELATION_NOT_FOUND = 2004
    INVALID_RELATION = 2005
    RELATION_ALREADY_EXISTS = 2006
    INVALID_CUSTOM_FIELDS = 2007
    INVALID_ASSIGNEE = 2008
    PROJECT_ARCHIVED = 2009
    # 3xxx: intake (reserved)
    # 4xxx: identity
    SETUP_ALREADY_COMPLETED = 4001
    INVALID_CREDENTIALS = 4002
    USER_DISABLED = 4003
    EMAIL_ALREADY_EXISTS = 4004
    INVITE_NOT_FOUND = 4005
    INVITE_EXPIRED = 4006
    INVITE_ALREADY_ACCEPTED = 4007
    INVITE_REVOKED = 4008
    DELEGATION_TOKEN_INVALID = 4009
    DELEGATION_TOKEN_EXPIRED = 4010
    CANNOT_MODIFY_OWNER = 4011
    PASSWORD_TOO_WEAK = 4012
    # 5xxx: projects
    PROJECT_KEY_EXISTS = 5001
    PROJECT_NOT_FOUND = 5002
    MEMBER_ALREADY_EXISTS = 5003
    MEMBER_NOT_FOUND = 5004
    CANNOT_MANAGE_OWNER_MEMBERSHIP = 5005
    # 6xxx: skills / MCP
    MCP_SERVER_TOKEN_INVALID = 6001
    MCP_DELEGATION_MISSING = 6002
    SKILL_RISK_FORBIDDEN = 6003
    SKILL_CONFIRMATION_REQUIRED = 6004
    SKILL_INVOCATION_NOT_FOUND = 6005


class BizError(Exception):
    def __init__(self, code: ErrorCode, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BizError)
    async def biz_error_handler(_: Request, exc: BizError) -> JSONResponse:
        status = {ErrorCode.UNAUTHORIZED: 401, ErrorCode.FORBIDDEN: 403}.get(exc.code, 200)
        return JSONResponse(status_code=status, content={"code": int(exc.code), "message": exc.message})

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error", exc_info=exc)
        return JSONResponse(status_code=500, content={"code": int(ErrorCode.INTERNAL), "message": "internal error"})
