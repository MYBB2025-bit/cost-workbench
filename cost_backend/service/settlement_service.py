"""结算业务层。"""

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import CostSettlement, CostSettlementItem
from repository import settlement_repo


async def list_settlements(
    db: AsyncSession,
    project_ids: list[int] | None,
    project_id: int | None = None,
) -> list[CostSettlement]:
    if project_id is not None and project_ids is not None and project_id not in project_ids:
        return []
    return await settlement_repo.list_settlements(
        db, project_ids=project_ids, project_id=project_id
    )


async def get_settlement(
    db: AsyncSession, settlement_id: int, project_ids: list[int] | None
) -> CostSettlement | None:
    row = await settlement_repo.get_settlement(db, settlement_id)
    if not row:
        return None
    if project_ids is not None and row.project_id not in project_ids:
        return None
    return row


async def create_settlement(
    db: AsyncSession, data: dict, user_id: int
) -> CostSettlement:
    data = dict(data)
    data["creator"] = user_id
    return await settlement_repo.create_settlement(db, data)


async def update_settlement(
    db: AsyncSession, settlement_id: int, data: dict, project_ids: list[int] | None
) -> CostSettlement | None:
    row = await get_settlement(db, settlement_id, project_ids)
    if not row:
        return None
    return await settlement_repo.update_settlement(db, row, data)


async def delete_settlement(
    db: AsyncSession, settlement_id: int, project_ids: list[int] | None
) -> bool:
    row = await get_settlement(db, settlement_id, project_ids)
    if not row:
        return False
    await settlement_repo.delete_settlement(db, row)
    return True


# ---------- 结算明细 ----------
async def list_settlement_items(
    db: AsyncSession, settlement_id: int
) -> list[CostSettlementItem]:
    return await settlement_repo.list_settlement_items(db, settlement_id)


async def create_settlement_item(
    db: AsyncSession, settlement_id: int, data: dict
) -> CostSettlementItem:
    data = dict(data)
    data["settlement_id"] = settlement_id
    return await settlement_repo.create_settlement_item(db, data)


async def update_settlement_item(
    db: AsyncSession, item_id: int, data: dict
) -> CostSettlementItem | None:
    row = await settlement_repo.get_settlement_item(db, item_id)
    if not row:
        return None
    return await settlement_repo.update_settlement_item(db, row, data)


async def delete_settlement_item(db: AsyncSession, item_id: int) -> bool:
    row = await settlement_repo.get_settlement_item(db, item_id)
    if not row:
        return False
    await settlement_repo.delete_settlement_item(db, row)
    return True
