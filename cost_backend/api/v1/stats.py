"""造价总览统计路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_user_project_ids
from db.session import get_db
from service import stats_service

router = APIRouter(prefix="/stats", tags=["统计"])


@router.get("/cost-overview")
async def cost_overview(
    project_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    project_ids=Depends(get_user_project_ids),
):
    if project_ids is not None and project_id is not None and project_id not in project_ids:
        raise HTTPException(status_code=403, detail="无该项目数据权限")
    return await stats_service.cost_overview(db, project_ids, project_id)
