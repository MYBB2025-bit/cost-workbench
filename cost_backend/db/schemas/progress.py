"""进度款 Schema。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProgressPaymentCreate(BaseModel):
    project_id: int
    period_name: str | None = None
    apply_amount: float = 0
    audit_amount: float = 0
    status: str | None = None


class ProgressPaymentUpdate(BaseModel):
    project_id: int | None = None
    period_name: str | None = None
    apply_amount: float | None = None
    audit_amount: float | None = None
    status: str | None = None


class ProgressPaymentResp(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int | None
    period_name: str | None
    apply_amount: float
    audit_amount: float
    status: str | None
    creator: int | None
    created_at: datetime


class PaymentNodeCreate(BaseModel):
    project_id: int
    parent_id: int | None = None
    name: str | None = None
    estimate: float = 0
    applied: float = 0
    audited: float = 0
    status: str | None = None
    sort_order: int = 0


class PaymentNodeUpdate(BaseModel):
    project_id: int | None = None
    parent_id: int | None = None
    name: str | None = None
    estimate: float | None = None
    applied: float | None = None
    audited: float | None = None
    status: str | None = None
    sort_order: int | None = None


class PaymentNodeResp(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int | None
    parent_id: int | None
    name: str | None
    estimate: float
    applied: float
    audited: float
    status: str | None
    sort_order: int
    children: list["PaymentNodeResp"] = []
