"""项目业务层：数据权限过滤 + 审计。"""

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import CostProject
from repository import project_repo


async def list_projects(db: AsyncSession, project_ids: list[int]) -> list[CostProject]:
    # 超级管理员 project_ids 为全部；普通用户仅可见授权项目
    return await project_repo.list_projects(db, project_ids)


async def get_project(db: AsyncSession, pid: int, project_ids: list[int]) -> CostProject | None:
    proj = await project_repo.get_project(db, pid)
    if proj and project_ids and proj.id not in project_ids:
        return None
    return proj


async def create_project(db: AsyncSession, data: dict, project_ids: list[int], user_id: int) -> CostProject:
    proj = await project_repo.create_project(db, data)
    # 创建者自动获得该项目数据权限
    from db.models import SysUserProjectPerm

    db.add(SysUserProjectPerm(user_id=user_id, project_id=proj.id))
    await db.commit()
    if project_ids is not None and proj.id not in project_ids:
        project_ids.append(proj.id)
    return proj


async def update_project(db: AsyncSession, pid: int, data: dict, project_ids: list[int]) -> CostProject | None:
    proj = await get_project(db, pid, project_ids)
    if not proj:
        return None
    return await project_repo.update_project(db, proj, data)


async def delete_project(db: AsyncSession, pid: int, project_ids: list[int]) -> bool:
    if project_ids and pid not in project_ids:
        return False
    await project_repo.delete_project(db, pid)
    return True
