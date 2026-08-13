"""核价库 Schema。"""

from pydantic import BaseModel, ConfigDict, Field


class PricingCreate(BaseModel):
    project_id: int | None = None
    name: str | None = Field(default=None, max_length=255)
    spec: str | None = Field(default=None, max_length=255)
    unit: str | None = Field(default=None, max_length=32)
    category: str | None = Field(default=None, max_length=64)
    supplier: str | None = Field(default=None, max_length=128)
    price: float = 0
    qty: float = 0


class PricingUpdate(BaseModel):
    project_id: int | None = None
    name: str | None = Field(default=None, max_length=255)
    spec: str | None = Field(default=None, max_length=255)
    unit: str | None = Field(default=None, max_length=32)
    category: str | None = Field(default=None, max_length=64)
    supplier: str | None = Field(default=None, max_length=128)
    price: float | None = None
    qty: float | None = None


class PricingResp(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int | None
    name: str | None
    spec: str | None
    unit: str | None
    category: str | None
    supplier: str | None
    price: float
    qty: float
    total: float
