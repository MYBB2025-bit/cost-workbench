"""工程项目 Schema。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    project_name: str = Field(..., min_length=1, max_length=255)
    project_code: str | None = Field(default=None, max_length=64)
    contract_amount: float | None = None
    status: str | None = "active"


class ProjectUpdate(BaseModel):
    project_name: str | None = Field(default=None, max_length=255)
    project_code: str | None = Field(default=None, max_length=64)
    contract_amount: float | None = None
    status: str | None = None


class ProjectResp(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_name: str
    project_code: str | None = None
    contract_amount: float | None = None
    status: str | None = None
    created_at: datetime
