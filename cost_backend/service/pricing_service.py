"""核价库业务层：总价 = 单价 × 工程量（修复原 CSV 导入计算口径）。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import CostPricing


def calc_total(price, qty) -> float:
    try:
        return round(float(price or 0) * float(qty or 0), 4)
    except (TypeError, ValueError):
        return 0.0


async def list_pricing(db: AsyncSession, project_id: int | None = None) -> list[CostPricing]:
    stmt = select(CostPricing)
    if project_id is not None:
        stmt = stmt.where(CostPricing.project_id == project_id)
    res = await db.execute(stmt.order_by(CostPricing.id.desc()))
    return list(res.scalars().all())


async def create_pricing(db: AsyncSession, data: dict) -> CostPricing:
    price = data.get("price", 0)
    qty = data.get("qty", 0)
    data = dict(data)
    data["total"] = calc_total(price, qty)
    row = CostPricing(**data)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def update_pricing(db: AsyncSession, pid: int, data: dict) -> CostPricing | None:
    row = await db.get(CostPricing, pid)
    if not row:
        return None
    if "price" in data or "qty" in data:
        price = data.get("price", row.price)
        qty = data.get("qty", row.qty)
        data = dict(data)
        data["total"] = calc_total(price, qty)
    for k, v in data.items():
        if hasattr(row, k):
            setattr(row, k, v)
    await db.commit()
    await db.refresh(row)
    return row
