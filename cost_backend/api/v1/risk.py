"""风险与预警路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_user_project_ids
from db.session import get_db
from service import risk_service

router = APIRouter(prefix="/risk", tags=["风险与预警"])


@router.get("/items")
async def risk_items(db: AsyncSession = Depends(get_db),
                    project_ids=Depends(get_user_project_ids)):
    return await risk_service.collect_risk_items(db, project_ids)


@router.get("/warnings")
async def warning_items(db: AsyncSession = Depends(get_db),
                       project_ids=Depends(get_user_project_ids)):
    return await risk_service.collect_warning_items(db, project_ids)
