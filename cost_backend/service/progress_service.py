"""进度款业务层（按用户提供的逻辑）。"""

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import CostProgressPayment
from repository import progress_repo


async def list_progress(db: AsyncSession, project_ids: list[int]) -> list[CostProgressPayment]:
    return await progress_repo.list_progress(db, project_ids)


async def create_progress(db: AsyncSession, data: dict) -> CostProgressPayment:
    return await progress_repo.create_progress(db, data)


async def list_payment_nodes(db: AsyncSession, project_id: int):
    return await progress_repo.list_payment_nodes(db, project_id)


async def upsert_payment_node(db: AsyncSession, data: dict):
    return await progress_repo.upsert_payment_node(db, data)
