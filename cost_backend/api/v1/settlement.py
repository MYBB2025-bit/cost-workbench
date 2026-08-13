"""结算路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_user_project_ids, require_perm
from db.schemas import (
    SettlementCreate,
    SettlementDetailResp,
    SettlementItemCreate,
    SettlementItemResp,
    SettlementItemUpdate,
    SettlementResp,
    SettlementUpdate,
)
from db.session import get_db
from service import settlement_service

router = APIRouter(prefix="/settlement", tags=["结算"])


# ---------- 结算单 ----------
@router.get("/list", response_model=list[SettlementResp])
async def settlement_list(
    project_id: int = None,
    db: AsyncSession = Depends(get_db),
    project_ids=Depends(get_user_project_ids),
):
    return await settlement_service.list_settlements(db, project_ids, project_id)


@router.get("/{settlement_id}", response_model=SettlementDetailResp)
async def settlement_detail(
    settlement_id: int,
    db: AsyncSession = Depends(get_db),
    project_ids=Depends(get_user_project_ids),
):
    row = await settlement_service.get_settlement(db, settlement_id, project_ids)
    if not row:
        raise HTTPException(status_code=404, detail="结算单不存在或无权限")
    items = await settlement_service.list_settlement_items(db, settlement_id)
    return {**row.__dict__, "items": items}


@router.post("/create", dependencies=[Depends(require_perm("settlement:create"))], response_model=SettlementResp)
async def settlement_create(
    body: SettlementCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    return await settlement_service.create_settlement(
        db, body.model_dump(), user["user_id"]
    )


@router.put("/{settlement_id}", dependencies=[Depends(require_perm("settlement:update"))], response_model=SettlementResp)
async def settlement_update(
    settlement_id: int,
    body: SettlementUpdate,
    db: AsyncSession = Depends(get_db),
    project_ids=Depends(get_user_project_ids),
):
    row = await settlement_service.update_settlement(
        db, settlement_id, body.model_dump(exclude_unset=True), project_ids
    )
    if not row:
        raise HTTPException(status_code=404, detail="结算单不存在或无权限")
    return row


@router.delete("/{settlement_id}", dependencies=[Depends(require_perm("settlement:delete"))])
async def settlement_delete(
    settlement_id: int,
    db: AsyncSession = Depends(get_db),
    project_ids=Depends(get_user_project_ids),
):
    ok = await settlement_service.delete_settlement(db, settlement_id, project_ids)
    if not ok:
        raise HTTPException(status_code=404, detail="结算单不存在或无权限")
    return {"deleted": True}


# ---------- 结算明细 ----------
@router.get("/{settlement_id}/items", response_model=list[SettlementItemResp])
async def settlement_item_list(
    settlement_id: int, db: AsyncSession = Depends(get_db)
):
    return await settlement_service.list_settlement_items(db, settlement_id)


@router.post(
    "/{settlement_id}/items",
    dependencies=[Depends(require_perm("settlement:update"))],
    response_model=SettlementItemResp,
)
async def settlement_item_create(
    settlement_id: int,
    body: SettlementItemCreate,
    db: AsyncSession = Depends(get_db),
):
    return await settlement_service.create_settlement_item(
        db, settlement_id, body.model_dump()
    )


@router.put(
    "/items/{item_id}",
    dependencies=[Depends(require_perm("settlement:update"))],
    response_model=SettlementItemResp,
)
async def settlement_item_update(
    item_id: int,
    body: SettlementItemUpdate,
    db: AsyncSession = Depends(get_db),
):
    row = await settlement_service.update_settlement_item(
        db, item_id, body.model_dump(exclude_unset=True)
    )
    if not row:
        raise HTTPException(status_code=404, detail="结算明细不存在")
    return row


@router.delete(
    "/items/{item_id}", dependencies=[Depends(require_perm("settlement:update"))]
)
async def settlement_item_delete(item_id: int, db: AsyncSession = Depends(get_db)):
    ok = await settlement_service.delete_settlement_item(db, item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="结算明细不存在")
    return {"deleted": True}
