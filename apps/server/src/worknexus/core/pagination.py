from typing import Annotated

from fastapi import Depends, Query
from pydantic import BaseModel, Field

from worknexus.core.schemas import ApiModel


class PageParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


async def get_page_params(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


PageParamsDep = Annotated[PageParams, Depends(get_page_params)]


class Page[T](ApiModel):
    items: list[T]
    total: int
    page: int
    page_size: int

    @classmethod
    def build(cls, items: list[T], total: int, params: PageParams) -> "Page[T]":
        return cls(items=items, total=total, page=params.page, page_size=params.page_size)
