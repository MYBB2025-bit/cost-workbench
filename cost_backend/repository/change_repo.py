"""变更签证数据层。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import CostChangeItem, CostChangeOrder, CostVisa


# ---------- 变更单 ----------
async def list_change_orders(
    db: AsyncSession,
    project_ids: list[int] | None = None,
    project_id: int | None = None,
) -> list[CostChangeOrder]:
    stmt = select(CostChangeOrder)
    if project_id is not None:
        stmt = stmt.where(CostChangeOrder.project_id == project_id)
    elif project_ids is not None:
        if not project_ids:
            return []
        stmt = stmt.where(CostChangeOrder.project_id.in_(project_ids))
    res = await db.execute(stmt.order_by(CostChangeOrder.id.desc()))
    return list(res.scalars().all())


async def get_change_order(db: AsyncSession, change_id: int) -> CostChangeOrder | None:
    return await db.get(CostChangeOrder, change_id)


async def create_change_order(db: AsyncSession, data: dict) -> CostChangeOrder:
    row = CostChangeOrder(**data)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def update_change_order(
    db: AsyncSession, row: CostChangeOrder, data: dict
) -> CostChangeOrder:
    for k, v in data.items():
        if k != "id" and hasattr(row, k):
            setattr(row, k, v)
    await db.commit()
    await db.refresh(row)
    return row


async def delete_change_order(db: AsyncSession, row: CostChangeOrder) -> None:
    await db.delete(row)
    await db.commit()


# ---------- 变更明细 ----------
async def list_change_items(db: AsyncSession, change_order_id: int) -> list[CostChangeItem]:
    res = await db.execute(
        select(CostChangeItem)
        .where(CostChangeItem.change_order_id == change_order_id)
        .order_by(CostChangeItem.sort_order, CostChangeItem.id)
    )
    return list(res.scalars().all())


async def get_change_item(db: AsyncSession, item_id: int) -> CostChangeItem | None:
    return await db.get(CostChangeItem, item_id)


async def create_change_item(db: AsyncSession, data: dict) -> CostChangeItem:
    row = CostChangeItem(**data)
    # 自动计算 delta_qty 与 amount
    if row.delta_qty == 0 and (row.after_qty or row.before_qty):
        row.delta_qty = float(row.after_qty or 0) - float(row.before_qty or 0)
    if row.amount == 0:
        row.amount = float(row.delta_qty or 0) * float(row.unit_price or 0)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def update_change_item(
    db: AsyncSession, row: CostChangeItem, data: dict
) -> CostChangeItem:
    for k, v in data.items():
        if k != "id" and hasattr(row, k):
            setattr(row, k, v)
    row.delta_qty = float(row.after_qty or 0) - float(row.before_qty or 0)
    row.amount = float(row.delta_qty or 0) * float(row.unit_price or 0)
    await db.commit()
    await db.refresh(row)
    return row


async def delete_change_item(db: AsyncSession, row: CostChangeItem) -> None:
    await db.delete(row)
    await db.commit()


# ---------- 签证 ----------
async def list_visas(
    db: AsyncSession,
    project_ids: list[int] | None = None,
    project_id: int | None = None,
) -> list[CostVisa]:
    stmt = select(CostVisa)
    if project_id is not None:
        stmt = stmt.where(CostVisa.project_id == project_id)
    elif project_ids is not None:
        if not project_ids:
            return []
        stmt = stmt.where(CostVisa.project_id.in_(project_ids))
    res = await db.execute(stmt.order_by(CostVisa.id.desc()))
    return list(res.scalars().all())


async def get_visa(db: AsyncSession, visa_id: int) -> CostVisa | None:
    return await db.get(CostVisa, visa_id)


async def create_visa(db: AsyncSession, data: dict) -> CostVisa:
    row = CostVisa(**data)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def update_visa(db: AsyncSession, row: CostVisa, data: dict) -> CostVisa:
    for k, v in data.items():
        if k != "id" and hasattr(row, k):
            setattr(row, k, v)
    await db.commit()
    await db.refresh(row)
    return row


async def delete_visa(db: AsyncSession, row: CostVisa) -> None:
    await db.delete(row)
    await db.commit()
