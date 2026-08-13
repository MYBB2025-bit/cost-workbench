"""风险与预警路由。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_user_project_ids, require_perm
from db.schemas import RiskItemCreate, RiskItemUpdate
from db.session import get_db
from service import risk_service

router = APIRouter(prefix="/risk", tags=["风险与预警"])


@router.get("/items")
async def risk_items(db: AsyncSession = Depends(get_db),
                    project_ids=Depends(get_user_project_ids)):
    return await risk_service.collect_risk_items(db, project_ids)


@router.post("/items", dependencies=[Depends(require_perm("risk:create"))])
async def risk_item_create(payload: RiskItemCreate,
                           db: AsyncSession = Depends(get_db),
                           user=Depends(get_current_user)):
    return await risk_service.create_risk_item(db, payload.model_dump())


@router.put("/items/{item_id}", dependencies=[Depends(require_perm("risk:update"))])
async def risk_item_update(item_id: int, payload: RiskItemUpdate,
                           db: AsyncSession = Depends(get_db)):
    updated = await risk_service.update_risk_item(db, item_id, payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="风险项不存在")
    return updated


@router.delete("/items/{item_id}", dependencies=[Depends(require_perm("risk:delete"))])
async def risk_item_delete(item_id: int, db: AsyncSession = Depends(get_db)):
    if not await risk_service.delete_risk_item(db, item_id):
        raise HTTPException(status_code=404, detail="风险项不存在")
    return {"ok": True}


@router.get("/warnings")
async def warning_items(db: AsyncSession = Depends(get_db),
                       project_ids=Depends(get_user_project_ids)):
    return await risk_service.collect_warning_items(db, project_ids)
