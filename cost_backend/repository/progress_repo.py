"""进度款数据层。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import CostPaymentNode, CostProgressPayment


async def list_progress(db: AsyncSession, project_ids: list[int]) -> list[CostProgressPayment]:
    if not project_ids:
        return []
    stmt = select(CostProgressPayment).where(CostProgressPayment.project_id.in_(project_ids))
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def create_progress(db: AsyncSession, data: dict) -> CostProgressPayment:
    row = CostProgressPayment(**data)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def list_payment_nodes(db: AsyncSession, project_id: int) -> list[CostPaymentNode]:
    res = await db.execute(
        select(CostPaymentNode)
        .where(CostPaymentNode.project_id == project_id)
        .order_by(CostPaymentNode.sort_order)
    )
    return list(res.scalars().all())


async def upsert_payment_node(db: AsyncSession, data: dict) -> CostPaymentNode:
    node_id = data.get("id")
    if node_id:
        node = await db.get(CostPaymentNode, node_id)
        if node:
            for k, v in data.items():
                if k != "id" and hasattr(node, k):
                    setattr(node, k, v)
    else:
        node = CostPaymentNode(**{k: v for k, v in data.items() if k != "id"})
        db.add(node)
    await db.commit()
    await db.refresh(node)
    return node
