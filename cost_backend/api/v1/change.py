"""变更签证路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_user_project_ids, require_perm
from db.schemas import (
    ChangeItemCreate,
    ChangeItemResp,
    ChangeItemUpdate,
    ChangeOrderCreate,
    ChangeOrderDetailResp,
    ChangeOrderResp,
    ChangeOrderUpdate,
    VisaCreate,
    VisaResp,
    VisaUpdate,
)
from db.session import get_db
from service import change_service

router = APIRouter(prefix="/change", tags=["变更签证"])


# ---------- 变更单 ----------
@router.get("/list", response_model=list[ChangeOrderResp])
async def change_list(
    project_id: int = None,
    db: AsyncSession = Depends(get_db),
    project_ids=Depends(get_user_project_ids),
):
    return await change_service.list_change_orders(db, project_ids, project_id)


@router.get("/{change_id}", response_model=ChangeOrderDetailResp)
async def change_detail(
    change_id: int,
    db: AsyncSession = Depends(get_db),
    project_ids=Depends(get_user_project_ids),
):
    row = await change_service.get_change_order(db, change_id, project_ids)
    if not row:
        raise HTTPException(status_code=404, detail="变更单不存在或无权限")
    items = await change_service.list_change_items(db, change_id)
    return {
        **row.__dict__,
        "items": items,
    }


@router.post("/create", dependencies=[Depends(require_perm("change:create"))], response_model=ChangeOrderResp)
async def change_create(
    body: ChangeOrderCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    return await change_service.create_change_order(db, body.model_dump(), user["user_id"])


@router.put("/{change_id}", dependencies=[Depends(require_perm("change:update"))], response_model=ChangeOrderResp)
async def change_update(
    change_id: int,
    body: ChangeOrderUpdate,
    db: AsyncSession = Depends(get_db),
    project_ids=Depends(get_user_project_ids),
):
    row = await change_service.update_change_order(
        db, change_id, body.model_dump(exclude_unset=True), project_ids
    )
    if not row:
        raise HTTPException(status_code=404, detail="变更单不存在或无权限")
    return row


@router.delete("/{change_id}", dependencies=[Depends(require_perm("change:delete"))])
async def change_delete(
    change_id: int,
    db: AsyncSession = Depends(get_db),
    project_ids=Depends(get_user_project_ids),
):
    ok = await change_service.delete_change_order(db, change_id, project_ids)
    if not ok:
        raise HTTPException(status_code=404, detail="变更单不存在或无权限")
    return {"deleted": True}


# ---------- 变更明细 ----------
@router.get("/{change_id}/items", response_model=list[ChangeItemResp])
async def change_item_list(change_id: int, db: AsyncSession = Depends(get_db)):
    return await change_service.list_change_items(db, change_id)


@router.post("/{change_id}/items", dependencies=[Depends(require_perm("change:update"))], response_model=ChangeItemResp)
async def change_item_create(
    change_id: int,
    body: ChangeItemCreate,
    db: AsyncSession = Depends(get_db),
):
    return await change_service.create_change_item(db, change_id, body.model_dump())


@router.put("/items/{item_id}", dependencies=[Depends(require_perm("change:update"))], response_model=ChangeItemResp)
async def change_item_update(
    item_id: int,
    body: ChangeItemUpdate,
    db: AsyncSession = Depends(get_db),
):
    row = await change_service.update_change_item(
        db, item_id, body.model_dump(exclude_unset=True)
    )
    if not row:
        raise HTTPException(status_code=404, detail="变更明细不存在")
    return row


@router.delete("/items/{item_id}", dependencies=[Depends(require_perm("change:update"))])
async def change_item_delete(item_id: int, db: AsyncSession = Depends(get_db)):
    ok = await change_service.delete_change_item(db, item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="变更明细不存在")
    return {"deleted": True}


# ---------- 签证 ----------
@router.get("/visa/list", response_model=list[VisaResp])
async def visa_list(
    project_id: int = None,
    db: AsyncSession = Depends(get_db),
    project_ids=Depends(get_user_project_ids),
):
    return await change_service.list_visas(db, project_ids, project_id)


@router.post("/visa/create", dependencies=[Depends(require_perm("change:create"))], response_model=VisaResp)
async def visa_create(
    body: VisaCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    return await change_service.create_visa(db, body.model_dump(), user["user_id"])


@router.put("/visa/{visa_id}", dependencies=[Depends(require_perm("change:update"))], response_model=VisaResp)
async def visa_update(
    visa_id: int,
    body: VisaUpdate,
    db: AsyncSession = Depends(get_db),
    project_ids=Depends(get_user_project_ids),
):
    row = await change_service.update_visa(
        db, visa_id, body.model_dump(exclude_unset=True), project_ids
    )
    if not row:
        raise HTTPException(status_code=404, detail="签证不存在或无权限")
    return row


@router.delete("/visa/{visa_id}", dependencies=[Depends(require_perm("change:delete"))])
async def visa_delete(
    visa_id: int,
    db: AsyncSession = Depends(get_db),
    project_ids=Depends(get_user_project_ids),
):
    ok = await change_service.delete_visa(db, visa_id, project_ids)
    if not ok:
        raise HTTPException(status_code=404, detail="签证不存在或无权限")
    return {"deleted": True}
