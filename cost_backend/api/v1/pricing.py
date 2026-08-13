"""核价库路由。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_user_project_ids, require_perm
from db.session import get_db
from service import pricing_service

router = APIRouter(prefix="/pricing", tags=["核价库"])


@router.get("/list")
async def pricing_list(project_id: int = None, db: AsyncSession = Depends(get_db),
                       project_ids=Depends(get_user_project_ids)):
    if project_id is not None and project_ids and project_id not in project_ids:
        raise HTTPException(status_code=403, detail="无该项目数据权限")
    return await pricing_service.list_pricing(db, project_id)


@router.post("/create", dependencies=[Depends(require_perm("pricing:create"))])
async def pricing_create(body: dict, db: AsyncSession = Depends(get_db)):
    return await pricing_service.create_pricing(db, body)


@router.put("/{pid}", dependencies=[Depends(require_perm("pricing:update"))])
async def pricing_update(pid: int, body: dict, db: AsyncSession = Depends(get_db)):
    row = await pricing_service.update_pricing(db, pid, body)
    if not row:
        raise HTTPException(status_code=404, detail="核价记录不存在")
    return row
