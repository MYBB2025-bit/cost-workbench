"""异步任务作业服务层。"""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import TaskJob
from repository import task_repo


async def create_job(
    db: AsyncSession, task_type: str, created_by: int | None, meta: dict | None = None
) -> TaskJob:
    """创建一条待处理作业，返回带 job_uuid 的记录。"""
    job = await task_repo.create(
        db,
        {
            "job_uuid": uuid.uuid4().hex,
            "task_type": task_type,
            "status": "pending",
            "created_by": created_by,
            "result": meta or {},
        },
    )
    await db.commit()
    await db.refresh(job)
    return job


async def get_job(db: AsyncSession, job_uuid: str) -> TaskJob | None:
    return await task_repo.get_by_uuid(db, job_uuid)


def to_dict(job: TaskJob) -> dict:
    return {
        "job_id": job.job_uuid,
        "task_type": job.task_type,
        "status": job.status,
        "progress": job.progress,
        "total": job.total,
        "processed": job.processed,
        "result": job.result,
        "error": job.error,
        "created_by": job.created_by,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    }
