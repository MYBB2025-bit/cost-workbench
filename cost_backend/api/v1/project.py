"""工程项目路由：数据权限过滤。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_user_project_ids, require_perm
from db.session import get_db
from service import project_service

router = APIRouter(prefix="/project", tags=["工程项目"])


@router.get("/list")
async def project_list(db: AsyncSession = Depends(get_db),
                      project_ids=Depends(get_user_project_ids)):
    return await project_service.list_projects(db, project_ids)


@router.get("/{pid}")
async def project_detail(pid: int, db: AsyncSession = Depends(get_db),
                         project_ids=Depends(get_user_project_ids)):
    proj = await project_service.get_project(db, pid, project_ids)
    if not proj:
        raise HTTPException(status_code=404, detail="项目不存在或无权限")
    return proj


@router.post("/create", dependencies=[Depends(require_perm("project:create"))])
async def project_create(body: dict, db: AsyncSession = Depends(get_db),
                         project_ids=Depends(get_user_project_ids),
                         user=Depends(get_current_user)):
    return await project_service.create_project(db, body, project_ids, user["user_id"])


@router.put("/{pid}", dependencies=[Depends(require_perm("project:update"))])
async def project_update(pid: int, body: dict, db: AsyncSession = Depends(get_db),
                         project_ids=Depends(get_user_project_ids)):
    proj = await project_service.update_project(db, pid, body, project_ids)
    if not proj:
        raise HTTPException(status_code=404, detail="项目不存在或无权限")
    return proj


@router.delete("/{pid}", dependencies=[Depends(require_perm("project:delete"))])
async def project_delete(pid: int, db: AsyncSession = Depends(get_db),
                         project_ids=Depends(get_user_project_ids)):
    ok = await project_service.delete_project(db, pid, project_ids)
    if not ok:
        raise HTTPException(status_code=404, detail="项目不存在或无权限")
    return {"deleted": True}
