"""异步任务作业路由：状态查询与结果下载。"""
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user
from db.schemas import TaskJobResp
from db.session import get_db
from service import task_service

router = APIRouter(prefix="/task", tags=["异步任务"])


async def _load_job(job_uuid: str, user: dict, db: AsyncSession):
    job = await task_service.get_job(db, job_uuid)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    # 仅创建者或超级管理员可查看/下载
    if not user.get("is_super") and job.created_by not in (None, user["user_id"]):
        raise HTTPException(status_code=403, detail="无权查看该任务")
    return job


@router.get("/{job_uuid}", response_model=TaskJobResp)
async def task_status(
    job_uuid: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """轮询任务进度与结果。"""
    job = await _load_job(job_uuid, user, db)
    return task_service.to_dict(job)


@router.get("/{job_uuid}/download")
async def task_download(
    job_uuid: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """下载任务产出的文件（仅导出类任务，且需成功）。"""
    job = await _load_job(job_uuid, user, db)
    if job.status != "success":
        raise HTTPException(status_code=409, detail="任务尚未完成")
    result = job.result or {}
    path = result.get("file_path")
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="导出文件不存在")
    return FileResponse(path, filename=result.get("filename", "export.csv"))
