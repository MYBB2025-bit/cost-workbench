"""历史数据迁移路由（仅超级管理员）。

- GET  /migration/preview  只读预览：源文件体积 + 各实体计数
- POST /migration/run      触发迁移：创建 TaskJob 并派发 Celery 异步任务
前端可轮询 GET /task/{job_id} 查看进度（migrate_user_data_task 复用同一 TaskJob）。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, require_perm
from db.session import get_db
from service import migration_service, task_service
from tasks.job_tasks import migrate_user_data_task

router = APIRouter(prefix="/migration", tags=["历史数据迁移"])


@router.get("/preview", dependencies=[Depends(require_perm("*"))])
async def migration_preview():
    """预览待迁移文件的体积与各实体计数（不写库）。"""
    path = migration_service.get_migration_path()
    return await migration_service.preview_user_data(path)


@router.post("/run", dependencies=[Depends(require_perm("*"))])
async def migration_run(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """触发一次历史数据迁移（异步）。仅超级管理员可调用。"""
    path = migration_service.get_migration_path()
    job = await task_service.create_job(
        db, "user_data_migration", user["user_id"], {"file_path": path}
    )
    # 派发 Celery 任务；eager 模式下会同步执行完成
    migrate_user_data_task.delay(job.job_uuid, path, user["user_id"])
    return {"job_id": job.job_uuid, "status": job.status, "task_type": job.task_type}
