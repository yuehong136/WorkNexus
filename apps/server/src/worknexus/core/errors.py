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
