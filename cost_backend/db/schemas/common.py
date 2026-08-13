"""通用 Schema。"""
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PageParams(BaseModel):
    page: int = 1
    size: int = 20


class PageResp(BaseModel, Generic[T]):
    """通用分页响应。实例化时替换 T 为具体 Schema，如 PageResp[BudgetItemResp]。"""

    total: int = 0
    items: list[Any] = []


class Resp(BaseModel, Generic[T]):
    """可选的统一包装响应。data 用 Any 避免泛型运行时校验问题。"""

    code: int = 0
    msg: str = "ok"
    data: Any | None = None
