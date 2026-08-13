"""风险与预警 Schema。"""

from pydantic import BaseModel, ConfigDict, Field


class RiskItemCreate(BaseModel):
    project_id: int
    risk_type: str | None = Field(default=None, max_length=64)
    level: str | None = Field(default=None, max_length=32)
    title: str | None = Field(default=None, max_length=255)
    desc: str | None = None
    due: str | None = Field(default=None, max_length=32)
    status: str | None = Field(default=None, max_length=32)
    related_type: str | None = Field(default=None, max_length=64)
    related_id: int | None = None


class RiskItemUpdate(BaseModel):
    risk_type: str | None = Field(default=None, max_length=64)
    level: str | None = Field(default=None, max_length=32)
    title: str | None = Field(default=None, max_length=255)
    desc: str | None = None
    due: str | None = Field(default=None, max_length=32)
    status: str | None = Field(default=None, max_length=32)
    related_type: str | None = Field(default=None, max_length=64)
    related_id: int | None = None


class RiskItemResp(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int | None
    risk_type: str | None
    level: str | None
    title: str | None
    desc: str | None
    due: str | None
    status: str | None
    related_type: str | None
    related_id: int | None


class WarningRuleResp(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rule_type: str | None
    threshold_days: int
    enabled: int
