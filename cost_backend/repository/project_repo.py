"""项目数据层。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import CostProject


async def list_projects(db: AsyncSession, project_ids: list[int] | None = None) -> list[CostProject]:
    stmt = select(CostProject)
    if project_ids is not None:
        if not project_ids:
            return []
        stmt = stmt.where(CostProject.id.in_(project_ids))
    res = await db.execute(stmt.order_by(CostProject.id.desc()))
    return list(res.scalars().all())


async def get_project(db: AsyncSession, pid: int) -> CostProject | None:
    return await db.get(CostProject, pid)


async def create_project(db: AsyncSession, data: dict) -> CostProject:
    proj = CostProject(**data)
    db.add(proj)
    await db.commit()
    await db.refresh(proj)
    return proj


async def update_project(db: AsyncSession, proj: CostProject, data: dict) -> CostProject:
    for k, v in data.items():
        if hasattr(proj, k):
            setattr(proj, k, v)
    await db.commit()
    await db.refresh(proj)
    return proj


async def delete_project(db: AsyncSession, pid: int) -> None:
    proj = await db.get(CostProject, pid)
    if proj:
        await db.delete(proj)
        await db.commit()
