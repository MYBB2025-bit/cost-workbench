"""进度款审核路由（含 WBS 统计）。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_user_project_ids, require_perm
from db.session import get_db
from service import payment_service, progress_service

router = APIRouter(prefix="/progress", tags=["进度款审核"])


@router.get("/list")
async def progress_list(db: AsyncSession = Depends(get_db),
                       project_ids=Depends(get_user_project_ids)):
    return await progress_service.list_progress(db, project_ids)


@router.post("/create", dependencies=[Depends(require_perm("progress:create"))])
async def progress_create(body: dict, db: AsyncSession = Depends(get_db)):
    return await progress_service.create_progress(db, body)


@router.get("/payment-nodes/{project_id}")
async def payment_nodes(project_id: int, db: AsyncSession = Depends(get_db),
                        project_ids=Depends(get_user_project_ids)):
    if project_ids and project_id not in project_ids:
        raise HTTPException(status_code=403, detail="无该项目数据权限")
    nodes = await progress_service.list_payment_nodes(db, project_id)
    return payment_service.build_payment_tree(nodes)


@router.get("/payment-stats/{project_id}")
async def payment_stats(project_id: int, db: AsyncSession = Depends(get_db),
                        project_ids=Depends(get_user_project_ids)):
    if project_ids and project_id not in project_ids:
        raise HTTPException(status_code=403, detail="无该项目数据权限")
    nodes = await progress_service.list_payment_nodes(db, project_id)
    return payment_service.compute_payment_stats(nodes)


@router.post("/payment-node", dependencies=[Depends(require_perm("progress:update"))])
async def payment_node_upsert(body: dict, db: AsyncSession = Depends(get_db)):
    return await progress_service.upsert_payment_node(db, body)
