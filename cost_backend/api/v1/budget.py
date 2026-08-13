"""预算清单路由。"""
import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.deps import get_current_user, get_user_project_ids, require_perm
from db.schemas import BudgetItemCreate, BudgetItemResp, BudgetItemUpdate
from db.session import get_db
from service import budget_service, task_service
from tasks.job_tasks import import_budget_task
from utils.xlsx_import import parse_budget_xlsx

router = APIRouter(prefix="/budget", tags=["预算清单"])

# 大文件临时落盘目录（与 worker 共享，compose 下挂同一卷）
_IMPORT_DIR = os.path.join(settings.LOCAL_UPLOAD_DIR, "imports")
os.makedirs(_IMPORT_DIR, exist_ok=True)


@router.get("/list", response_model=list[BudgetItemResp])
async def budget_list(
    project_id: int = None,
    db: AsyncSession = Depends(get_db),
    project_ids=Depends(get_user_project_ids),
):
    return await budget_service.list_items(db, project_ids, project_id)


@router.get("/tree")
async def budget_tree(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    project_ids=Depends(get_user_project_ids),
):
    if project_ids and project_id not in project_ids:
        raise HTTPException(status_code=403, detail="无该项目数据权限")
    rows = await budget_service.list_items(db, project_ids, project_id)
    return budget_service.build_tree(rows)


@router.get("/{item_id}", response_model=BudgetItemResp)
async def budget_detail(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    project_ids=Depends(get_user_project_ids),
):
    row = await budget_service.get_item(db, item_id, project_ids)
    if not row:
        raise HTTPException(status_code=404, detail="清单项不存在或无权限")
    return row


@router.post("/create", dependencies=[Depends(require_perm("budget:create"))], response_model=BudgetItemResp)
async def budget_create(
    body: BudgetItemCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    return await budget_service.create_item(db, body.model_dump(), user["user_id"])


@router.put("/{item_id}", dependencies=[Depends(require_perm("budget:update"))], response_model=BudgetItemResp)
async def budget_update(
    item_id: int,
    body: BudgetItemUpdate,
    db: AsyncSession = Depends(get_db),
    project_ids=Depends(get_user_project_ids),
):
    row = await budget_service.update_item(db, item_id, body.model_dump(exclude_unset=True), project_ids)
    if not row:
        raise HTTPException(status_code=404, detail="清单项不存在或无权限")
    return row


@router.delete("/{item_id}", dependencies=[Depends(require_perm("budget:delete"))])
async def budget_delete(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    project_ids=Depends(get_user_project_ids),
):
    ok = await budget_service.delete_item(db, item_id, project_ids)
    if not ok:
        raise HTTPException(status_code=404, detail="清单项不存在或无权限")
    return {"deleted": True}


@router.post("/import", dependencies=[Depends(require_perm("budget:create"))])
async def budget_import(
    file: UploadFile = File(...),
    project_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    project_ids=Depends(get_user_project_ids),
):
    """Excel(xlsx) 批量导入预算清单。支持列：编号/名称/规格/单位/工程量/单价/分类/父级编号。"""
    if project_ids is not None and project_id not in project_ids:
        raise HTTPException(status_code=403, detail="无该项目数据权限")
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 文件")
    content = await file.read()
    try:
        rows = parse_budget_xlsx(content)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"解析 Excel 失败：{e}")
    if not rows:
        raise HTTPException(status_code=400, detail="文件中未解析到有效数据行")
    return await budget_service.bulk_import(db, project_id, rows, user["user_id"])


@router.post("/import-async", dependencies=[Depends(require_perm("budget:create"))])
async def budget_import_async(
    file: UploadFile = File(...),
    project_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    project_ids=Depends(get_user_project_ids),
):
    """Excel(xlsx) 异步批量导入（适配大文件，返回 job_id 供前端轮询）。

    大文件先落本地临时目录，再把路径交给 Celery worker 处理，
    避免请求长时间阻塞与消息队列承载大体积负载。
    """
    if project_ids is not None and project_id not in project_ids:
        raise HTTPException(status_code=403, detail="无该项目数据权限")
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 文件")

    job = await task_service.create_job(
        db, "budget_import", user["user_id"],
        {"project_id": project_id, "filename": file.filename},
    )
    ext = os.path.splitext(file.filename)[1] or ".xlsx"
    storage_path = os.path.join(_IMPORT_DIR, f"{job.job_uuid}{ext}")
    content = await file.read()
    with open(storage_path, "wb") as f:
        f.write(content)

    import_budget_task.delay(job.job_uuid, storage_path, project_id, user["user_id"])
    return {"job_id": job.job_uuid, "status": job.status}
