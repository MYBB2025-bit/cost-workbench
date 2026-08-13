"""结算 Schema。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------- 结算单 ----------
class SettlementCreate(BaseModel):
    project_id: int
    settlement_no: str | None = Field(default=None, max_length=64)
    settlement_name: str | None = Field(default=None, max_length=255)
    settlement_type: str | None = "midterm"
    total_amount: float = 0
    status: str | None = "draft"


class SettlementUpdate(BaseModel):
    settlement_no: str | None = Field(default=None, max_length=64)
    settlement_name: str | None = Field(default=None, max_length=255)
    settlement_type: str | None = None
    total_amount: float | None = None
    status: str | None = None


class SettlementResp(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int | None
    settlement_no: str | None
    settlement_name: str | None
    settlement_type: str | None
    total_amount: float
    status: str | None
    creator: int | None
    created_at: datetime


# ---------- 结算明细 ----------
class SettlementItemCreate(BaseModel):
    settlement_id: int | None = None
    budget_item_id: int | None = None
    name: str | None = Field(default=None, max_length=255)
    unit: str | None = Field(default=None, max_length=32)
    settle_qty: float = 0
    unit_price: float = 0
    amount: float = 0
    sort_order: int = 0


class SettlementItemUpdate(BaseModel):
    budget_item_id: int | None = None
    name: str | None = Field(default=None, max_length=255)
    unit: str | None = Field(default=None, max_length=32)
    settle_qty: float | None = None
    unit_price: float | None = None
    amount: float | None = None
    sort_order: int | None = None


class SettlementItemResp(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    settlement_id: int | None
    budget_item_id: int | None
    name: str | None
    unit: str | None
    settle_qty: float
    unit_price: float
    amount: float
    sort_order: int


class SettlementDetailResp(SettlementResp):
    items: list[SettlementItemResp] = []
