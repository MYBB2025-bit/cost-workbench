"""预算清单数据层。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import CostBudgetItem


async def list_items(
    db: AsyncSession,
    project_ids: list[int] | None = None,
    project_id: int | None = None,
) -> list[CostBudgetItem]:
    stmt = select(CostBudgetItem)
    if project_id is not None:
        stmt = stmt.where(CostBudgetItem.project_id == project_id)
    elif project_ids is not None:
        if not project_ids:
            return []
        stmt = stmt.where(CostBudgetItem.project_id.in_(project_ids))
    res = await db.execute(stmt.order_by(CostBudgetItem.sort_order, CostBudgetItem.id))
    return list(res.scalars().all())


async def get_item(db: AsyncSession, item_id: int) -> CostBudgetItem | None:
    return await db.get(CostBudgetItem, item_id)


async def create_item(db: AsyncSession, data: dict) -> CostBudgetItem:
    row = CostBudgetItem(**data)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def update_item(
    db: AsyncSession, item: CostBudgetItem, data: dict
) -> CostBudgetItem:
    for k, v in data.items():
        if k != "id" and hasattr(item, k):
            setattr(item, k, v)
    # 自动重算合价
    item.total_price = float(item.qty or 0) * float(item.unit_price or 0)
    await db.commit()
    await db.refresh(item)
    return item


async def delete_item(db: AsyncSession, item: CostBudgetItem) -> None:
    await db.delete(item)
    await db.commit()


async def bulk_create(db: AsyncSession, items: list[CostBudgetItem]) -> list[CostBudgetItem]:
    """批量写入（flush 后返回带 id 的对象，便于解析父子关系）。"""
    for it in items:
        db.add(it)
    await db.flush()
    return items
