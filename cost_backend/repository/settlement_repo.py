"""结算数据层。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import CostSettlement, CostSettlementItem


async def list_settlements(
    db: AsyncSession,
    project_ids: list[int] | None = None,
    project_id: int | None = None,
) -> list[CostSettlement]:
    stmt = select(CostSettlement)
    if project_id is not None:
        stmt = stmt.where(CostSettlement.project_id == project_id)
    elif project_ids is not None:
        if not project_ids:
            return []
        stmt = stmt.where(CostSettlement.project_id.in_(project_ids))
    res = await db.execute(stmt.order_by(CostSettlement.id.desc()))
    return list(res.scalars().all())


async def get_settlement(db: AsyncSession, settlement_id: int) -> CostSettlement | None:
    return await db.get(CostSettlement, settlement_id)


async def create_settlement(db: AsyncSession, data: dict) -> CostSettlement:
    row = CostSettlement(**data)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def update_settlement(
    db: AsyncSession, row: CostSettlement, data: dict
) -> CostSettlement:
    for k, v in data.items():
        if k != "id" and hasattr(row, k):
            setattr(row, k, v)
    await db.commit()
    await db.refresh(row)
    return row


async def delete_settlement(db: AsyncSession, row: CostSettlement) -> None:
    await db.delete(row)
    await db.commit()


# ---------- 结算明细 ----------
async def list_settlement_items(
    db: AsyncSession, settlement_id: int
) -> list[CostSettlementItem]:
    res = await db.execute(
        select(CostSettlementItem)
        .where(CostSettlementItem.settlement_id == settlement_id)
        .order_by(CostSettlementItem.sort_order, CostSettlementItem.id)
    )
    return list(res.scalars().all())


async def get_settlement_item(
    db: AsyncSession, item_id: int
) -> CostSettlementItem | None:
    return await db.get(CostSettlementItem, item_id)


async def create_settlement_item(db: AsyncSession, data: dict) -> CostSettlementItem:
    row = CostSettlementItem(**data)
    if row.amount == 0:
        row.amount = float(row.settle_qty or 0) * float(row.unit_price or 0)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def update_settlement_item(
    db: AsyncSession, row: CostSettlementItem, data: dict
) -> CostSettlementItem:
    for k, v in data.items():
        if k != "id" and hasattr(row, k):
            setattr(row, k, v)
    row.amount = float(row.settle_qty or 0) * float(row.unit_price or 0)
    await db.commit()
    await db.refresh(row)
    return row


async def delete_settlement_item(db: AsyncSession, row: CostSettlementItem) -> None:
    await db.delete(row)
    await db.commit()
