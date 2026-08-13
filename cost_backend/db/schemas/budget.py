"""预算清单 Schema。"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BudgetItemBase(BaseModel):
    project_id: int | None = None
    parent_id: int | None = None
    item_no: str | None = Field(default=None, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    spec: str | None = Field(default=None, max_length=255)
    unit: str | None = Field(default=None, max_length=32)
    qty: float = 0
    unit_price: float = 0
    category: str | None = Field(default=None, max_length=64)
    work_type: str | None = Field(default=None, max_length=64)
    sort_order: int = 0


class BudgetItemCreate(BudgetItemBase):
    project_id: int


class BudgetItemUpdate(BaseModel):
    parent_id: int | None = None
    item_no: str | None = Field(default=None, max_length=64)
    name: str | None = Field(default=None, max_length=255)
    spec: str | None = Field(default=None, max_length=255)
    unit: str | None = Field(default=None, max_length=32)
    qty: float | None = None
    unit_price: float | None = None
    category: str | None = Field(default=None, max_length=64)
    work_type: str | None = Field(default=None, max_length=64)
    sort_order: int | None = None


class BudgetItemResp(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int | None
    parent_id: int | None
    item_no: str | None
    name: str
    spec: str | None
    unit: str | None
    qty: float
    unit_price: float
    total_price: float
    category: str | None
    work_type: str | None
    sort_order: int
    created_at: datetime


class BudgetTreeResp(BaseModel):
    """树形预算清单节点。"""

    id: int
    project_id: int | None
    parent_id: int | None
    item_no: str | None
    name: str
    spec: str | None
    unit: str | None
    qty: float
    unit_price: float
    total_price: float
    category: str | None
    work_type: str | None
    sort_order: int
    children: list[Any] = []


class BudgetImportLogResp(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int | None
    filename: str | None
    total_rows: int
    success_rows: int
    error_rows: int
    errors: Any | None = None
    status: str | None
    uploaded_by: int | None
    created_at: datetime
