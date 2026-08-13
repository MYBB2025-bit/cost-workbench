"""变更签证 Schema。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------- 变更单 ----------
class ChangeOrderCreate(BaseModel):
    project_id: int
    change_no: str | None = Field(default=None, max_length=64)
    change_name: str | None = Field(default=None, max_length=255)
    change_type: str | None = Field(default=None, max_length=64)
    amount: float = 0
    status: str | None = "draft"


class ChangeOrderUpdate(BaseModel):
    change_no: str | None = Field(default=None, max_length=64)
    change_name: str | None = Field(default=None, max_length=255)
    change_type: str | None = Field(default=None, max_length=64)
    amount: float | None = None
    status: str | None = None


class ChangeOrderResp(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int | None
    change_no: str | None
    change_name: str | None
    change_type: str | None
    amount: float
    status: str | None
    creator: int | None
    created_at: datetime


class ChangeItemCreate(BaseModel):
    change_order_id: int | None = None
    budget_item_id: int | None = None
    name: str | None = Field(default=None, max_length=255)
    unit: str | None = Field(default=None, max_length=32)
    before_qty: float = 0
    after_qty: float = 0
    delta_qty: float = 0
    unit_price: float = 0
    amount: float = 0
    sort_order: int = 0


class ChangeItemUpdate(BaseModel):
    budget_item_id: int | None = None
    name: str | None = Field(default=None, max_length=255)
    unit: str | None = Field(default=None, max_length=32)
    before_qty: float | None = None
    after_qty: float | None = None
    delta_qty: float | None = None
    unit_price: float | None = None
    amount: float | None = None
    sort_order: int | None = None


class ChangeItemResp(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    change_order_id: int | None
    budget_item_id: int | None
    name: str | None
    unit: str | None
    before_qty: float
    after_qty: float
    delta_qty: float
    unit_price: float
    amount: float
    sort_order: int


class ChangeOrderDetailResp(ChangeOrderResp):
    items: list[ChangeItemResp] = []


# ---------- 签证 ----------
class VisaCreate(BaseModel):
    project_id: int
    visa_no: str | None = Field(default=None, max_length=64)
    visa_date: str | None = Field(default=None, max_length=32)
    content: str | None = None
    amount: float = 0
    status: str | None = "draft"


class VisaUpdate(BaseModel):
    visa_no: str | None = Field(default=None, max_length=64)
    visa_date: str | None = Field(default=None, max_length=32)
    content: str | None = None
    amount: float | None = None
    status: str | None = None


class VisaResp(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int | None
    visa_no: str | None
    visa_date: str | None
    content: str | None
    amount: float
    status: str | None
    creator: int | None
    created_at: datetime
