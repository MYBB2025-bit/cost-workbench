"""最终资料台账 Schema。"""

from pydantic import BaseModel, ConfigDict, Field


class LedgerDocCreate(BaseModel):
    project_id: int
    category: str | None = Field(default=None, max_length=64)
    name: str | None = Field(default=None, max_length=255)
    owner: str | None = Field(default=None, max_length=64)
    due: str | None = Field(default=None, max_length=32)
    status: str | None = Field(default=None, max_length=32)
    finished_at: str | None = Field(default=None, max_length=32)


class LedgerDocUpdate(BaseModel):
    category: str | None = Field(default=None, max_length=64)
    name: str | None = Field(default=None, max_length=255)
    owner: str | None = Field(default=None, max_length=64)
    due: str | None = Field(default=None, max_length=32)
    status: str | None = Field(default=None, max_length=32)
    finished_at: str | None = Field(default=None, max_length=32)


class LedgerDocResp(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int | None
    category: str | None
    name: str | None
    owner: str | None
    due: str | None
    status: str | None
    finished_at: str | None
