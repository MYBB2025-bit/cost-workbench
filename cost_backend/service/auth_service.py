"""认证与权限服务：登录校验、角色/权限聚合、数据权限（项目隔离）、初始管理员。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import create_access_token, get_password_hash, verify_password
from db.models import (
    CostProject,
    SysPermission,
    SysRole,
    SysRolePerm,
    SysUser,
    SysUserProjectPerm,
    SysUserRole,
)

# 初始角色
_BASE_ROLES = [
    ("cost_admin", "造价系统管理员"),
    ("cost_editor", "造价驻场员"),
    ("cost_leader", "部门负责人"),
    ("readonly_viewer", "只读审计"),
]
# 超级管理员持有的通配权限
_SUPER_PERM = "*"


async def get_user_by_username(db: AsyncSession, username: str) -> SysUser | None:
    res = await db.execute(select(SysUser).where(SysUser.username == username))
    return res.scalar_one_or_none()


async def authenticate(db: AsyncSession, username: str, password: str) -> SysUser | None:
    user = await get_user_by_username(db, username)
    if not user or user.status != 1:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def get_user_roles(db: AsyncSession, user_id: int) -> list[SysRole]:
    res = await db.execute(
        select(SysRole)
        .join(SysUserRole, SysUserRole.role_id == SysRole.id)
        .where(SysUserRole.user_id == user_id)
    )
    return list(res.scalars().all())


async def get_user_perms(db: AsyncSession, user_id: int) -> set[str]:
    user = await db.get(SysUser, user_id)
    if user and user.is_super:
        return {_SUPER_PERM}
    role_ids = (
        (await db.execute(select(SysUserRole.role_id).where(SysUserRole.user_id == user_id))).scalars().all()
    )
    if not role_ids:
        return set()
    perm_ids = (
        (await db.execute(select(SysRolePerm.perm_id).where(SysRolePerm.role_id.in_(role_ids)))).scalars().all()
    )
    res = await db.execute(select(SysPermission.perm_code).where(SysPermission.id.in_(perm_ids)))
    return set(res.scalars().all())


async def get_user_permission_projects(db: AsyncSession, user_id: int) -> list[int]:
    """【造价独有】返回用户可访问的项目ID。超级管理员返回全部。"""
    user = await db.get(SysUser, user_id)
    if user and user.is_super:
        res = await db.execute(select(CostProject.id))
        return list(res.scalars().all())
    res = await db.execute(
        select(SysUserProjectPerm.project_id).where(SysUserProjectPerm.user_id == user_id)
    )
    return list(res.scalars().all())


async def build_token(db: AsyncSession, user: SysUser) -> str:
    perms = await get_user_perms(db, user.id)
    roles = await get_user_roles(db, user.id)
    payload = {
        "sub": user.username,
        "user_id": user.id,
        "username": user.username,
        "real_name": user.real_name,
        "perms": list(perms),
        "roles": [r.role_code for r in roles],
    }
    return create_access_token(payload)


async def init_admin(db: AsyncSession) -> None:
    """首次启动创建超级管理员与基础角色。"""
    existing = await get_user_by_username(db, settings.INIT_ADMIN_USERNAME)
    if existing:
        return
    admin = SysUser(
        username=settings.INIT_ADMIN_USERNAME,
        real_name=settings.INIT_ADMIN_REAL_NAME,
        password_hash=get_password_hash(settings.INIT_ADMIN_PASSWORD),
        status=1,
        is_super=True,
    )
    db.add(admin)
    await db.flush()
    # 基础角色
    for code, name in _BASE_ROLES:
        db.add(SysRole(role_code=code, role_name=name, status=1))
    await db.commit()
