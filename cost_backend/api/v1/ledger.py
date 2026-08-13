"""最终资料台账路由。"""
import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_user_project_ids, require_perm
from db.session import get_db
from service import ledger_service, task_service
from tasks.job_tasks import export_ledger_task

router = APIRouter(prefix="/ledger", tags=["最终资料台账"])


@router.get("/list")
async def ledger_list(project_id: int = None,
                      db: AsyncSession = Depends(get_db),
                      project_ids=Depends(get_user_project_ids)):
    return await ledger_service.collect_final_ledger(db, project_ids, project_id)


@router.get("/export", dependencies=[Depends(require_perm("ledger:view"))])
async def ledger_export(project_id: int = None,
                        db: AsyncSession = Depends(get_db),
                        project_ids=Depends(get_user_project_ids)):
    """导出 CSV（带 BOM，Excel 可直接打开）。"""
    rows = await ledger_service.export_ledger(db, project_ids, project_id)
    headers = ["项目名称", "类别", "资料名称", "负责人", "截止", "状态", "完成时间"]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    for r in rows:
        writer.writerow([
            r["project_name"], r["category"], r["name"],
            r["owner"], r["due"], r["status"], r["finished_at"],
        ])
    # 加 BOM 头，避免中文乱码
    data = "\ufeff" + buf.getvalue()
    return StreamingResponse(
        iter([data]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="ledger_export.csv"'},
    )


@router.get("/export-async", dependencies=[Depends(require_perm("ledger:view"))])
async def ledger_export_async(
    project_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    project_ids=Depends(get_user_project_ids),
):
    """异步导出台账 CSV（适配大数据量，返回 job_id 供前端轮询下载）。"""
    if project_ids is not None and project_id is not None and project_id not in project_ids:
        raise HTTPException(status_code=403, detail="无该项目数据权限")
    job = await task_service.create_job(
        db, "ledger_export", user["user_id"], {"project_id": project_id}
    )
    # 超级管理员 project_ids 为 None（全部）；受限用户传具体列表
    export_ledger_task.delay(
        job.job_uuid, project_id, user["user_id"], project_ids if project_ids is not None else None
    )
    return {"job_id": job.job_uuid, "status": job.status}
