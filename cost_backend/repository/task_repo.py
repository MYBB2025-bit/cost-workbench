"""异步任务作业数据层。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import TaskJob


async def get_by_uuid(db: AsyncSession, job_uuid: str) -> TaskJob | None:
    res = await db.execute(select(TaskJob).where(TaskJob.job_uuid == job_uuid))
    return res.scalars().first()


async def create(db: AsyncSession, data: dict) -> TaskJob:
    job = TaskJob(**data)
    db.add(job)
    await db.flush()
    await db.refresh(job)
    return job


async def update_fields(db: AsyncSession, job: TaskJob, **fields) -> TaskJob:
    for k, v in fields.items():
        setattr(job, k, v)
    await db.flush()
    return job
