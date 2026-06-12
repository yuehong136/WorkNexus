from typing import Any

from pydantic import BaseModel


class Envelope[T](BaseModel):
    code: int = 0
    message: str = "ok"
    data: T | None = None


def ok(data: Any = None) -> dict[str, Any]:
    return {"code": 0, "message": "ok", "data": data}
