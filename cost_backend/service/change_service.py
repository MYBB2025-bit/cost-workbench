"""变更签证业务层。"""

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import CostChangeItem, CostChangeOrder, CostVisa
from repository import change_repo


async def list_change_orders(
    db: AsyncSession,
    project_ids: list[int] | None,
    project_id: int | None = None,
) -> list[CostChangeOrder]:
    if project_id is not None and project_ids is not None and project_id not in project_ids:
        return []
    return await change_repo.list_change_orders(
        db, project_ids=project_ids, project_id=project_id
    )


async def get_change_order(
    db: AsyncSession, change_id: int, project_ids: list[int] | None
) -> CostChangeOrder | None:
    row = await change_repo.get_change_order(db, change_id)
    if not row:
        return None
    if project_ids is not None and row.project_id not in project_ids:
        return None
    return row


async def create_change_order(
    db: AsyncSession, data: dict, user_id: int
) -> CostChangeOrder:
    data = dict(data)
    data["creator"] = user_id
    return await change_repo.create_change_order(db, data)


async def update_change_order(
    db: AsyncSession, change_id: int, data: dict, project_ids: list[int] | None
) -> CostChangeOrder | None:
    row = await get_change_order(db, change_id, project_ids)
    if not row:
        return None
    return await change_repo.update_change_order(db, row, data)


async def delete_change_order(
    db: AsyncSession, change_id: int, project_ids: list[int] | None
) -> bool:
    row = await get_change_order(db, change_id, project_ids)
    if not row:
        return False
    await change_repo.delete_change_order(db, row)
    return True


# ---------- 变更明细 ----------
async def list_change_items(db: AsyncSession, change_order_id: int) -> list[CostChangeItem]:
    return await change_repo.list_change_items(db, change_order_id)


async def create_change_item(db: AsyncSession, change_order_id: int, data: dict) -> CostChangeItem:
    data = dict(data)
    data["change_order_id"] = change_order_id
    return await change_repo.create_change_item(db, data)


async def update_change_item(
    db: AsyncSession, item_id: int, data: dict
) -> CostChangeItem | None:
    row = await change_repo.get_change_item(db, item_id)
    if not row:
        return None
    return await change_repo.update_change_item(db, row, data)


async def delete_change_item(db: AsyncSession, item_id: int) -> bool:
    row = await change_repo.get_change_item(db, item_id)
    if not row:
        return False
    await change_repo.delete_change_item(db, row)
    return True


# ---------- 签证 ----------
async def list_visas(
    db: AsyncSession,
    project_ids: list[int] | None,
    project_id: int | None = None,
) -> list[CostVisa]:
    if project_id is not None and project_ids is not None and project_id not in project_ids:
        return []
    return await change_repo.list_visas(db, project_ids=project_ids, project_id=project_id)


async def get_visa(
    db: AsyncSession, visa_id: int, project_ids: list[int] | None
) -> CostVisa | None:
    row = await change_repo.get_visa(db, visa_id)
    if not row:
        return None
    if project_ids is not None and row.project_id not in project_ids:
        return None
    return row


async def create_visa(db: AsyncSession, data: dict, user_id: int) -> CostVisa:
    data = dict(data)
    data["creator"] = user_id
    return await change_repo.create_visa(db, data)


async def update_visa(
    db: AsyncSession, visa_id: int, data: dict, project_ids: list[int] | None
) -> CostVisa | None:
    row = await get_visa(db, visa_id, project_ids)
    if not row:
        return None
    return await change_repo.update_visa(db, row, data)


async def delete_visa(db: AsyncSession, visa_id: int, project_ids: list[int] | None) -> bool:
    row = await get_visa(db, visa_id, project_ids)
    if not row:
        return False
    await change_repo.delete_visa(db, row)
    return True
