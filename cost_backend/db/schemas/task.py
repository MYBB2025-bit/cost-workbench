"""异步任务作业 Schema。"""
from typing import Any

from pydantic import BaseModel, ConfigDict


class TaskJobResp(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: str
    task_type: str
    status: str
    progress: int = 0
    total: int = 0
    processed: int = 0
    result: dict[str, Any] | None = None
    error: str | None = None
    created_by: int | None = None
    created_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
