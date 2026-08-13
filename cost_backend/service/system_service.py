"""系统管理：用户、角色、权限、灰度发布配置的后台服务。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_password_hash
from db.models import (
    ClientGrayRelease,
    CostProject,
    SysPermission,
    SysRole,
    SysRolePerm,
    SysUser,
    SysUserProjectPerm,
    SysUserRole,
)


# ============ 用户 ============
async def list_users(db: AsyncSession) -> list[dict]:
    res = await db.execute(select(SysUser).order_by(SysUser.id.desc()))
    users = res.scalars().all()
    out = []
    for u in users:
        role_res = await db.execute(
            select(SysRole.role_code, SysRole.role_name)
            .join(SysUserRole, SysUserRole.role_id == SysRole.id)
            .where(SysUserRole.user_id == u.id)
        )
        roles = [{"role_code": r[0], "role_name": r[1]} for r in role_res.all()]
        proj_res = await db.execute(
            select(SysUserProjectPerm.project_id).where(SysUserProjectPerm.user_id == u.id)
        )
        project_ids = [r[0] for r in proj_res.all()]
        out.append(
            {
                "id": u.id,
                "username": u.username,
                "real_name": u.real_name,
                "status": u.status,
                "is_super": u.is_super,
                "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "roles": roles,
                "project_ids": project_ids,
            }
        )
    return out


async def create_user(db: AsyncSession, data: dict) -> SysUser:
    pwd = data.get("password") or "123456"
    user = SysUser(
        username=data["username"],
        real_name=data.get("real_name", data["username"]),
        password_hash=get_password_hash(pwd),
        status=int(data.get("status", 1)),
        is_super=bool(data.get("is_super", False)),
    )
    db.add(user)
    await db.flush()
    return user


async def update_user(db: AsyncSession, user_id: int, data: dict) -> SysUser | None:
    user = await db.get(SysUser, user_id)
    if not user:
        return None
    if "real_name" in data:
        user.real_name = data["real_name"]
    if "status" in data:
        user.status = int(data["status"])
    if "is_super" in data:
        user.is_super = bool(data["is_super"])
    if data.get("password"):
        user.password_hash = get_password_hash(data["password"])
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user_id: int) -> bool:
    user = await db.get(SysUser, user_id)
    if not user:
        return False
    await db.delete(user)
    await db.commit()
    return True


async def set_user_roles(db: AsyncSession, user_id: int, role_ids: list[int]) -> None:
    await db.execute(select(SysUser).where(SysUser.id == user_id))
    await db.execute(select(SysUserRole).where(SysUserRole.user_id == user_id))
    # 删除旧绑定
    await db.execute(
        SysUserRole.__table__.delete().where(SysUserRole.user_id == user_id)
    )
    for rid in set(role_ids or []):
        role = await db.get(SysRole, rid)
        if role:
            db.add(SysUserRole(user_id=user_id, role_id=rid))
    await db.commit()


async def set_user_projects(db: AsyncSession, user_id: int, project_ids: list[int]) -> None:
    await db.execute(
        SysUserProjectPerm.__table__.delete().where(SysUserProjectPerm.user_id == user_id)
    )
    for pid in set(project_ids or []):
        proj = await db.get(CostProject, pid)
        if proj:
            db.add(SysUserProjectPerm(user_id=user_id, project_id=pid))
    await db.commit()


# ============ 角色 ============
async def list_roles(db: AsyncSession) -> list[dict]:
    res = await db.execute(select(SysRole).order_by(SysRole.id.desc()))
    out = []
    for r in res.scalars().all():
        perm_res = await db.execute(
            select(SysPermission.perm_code, SysPermission.perm_name)
            .join(SysRolePerm, SysRolePerm.perm_id == SysPermission.id)
            .where(SysRolePerm.role_id == r.id)
        )
        perms = [{"perm_code": p[0], "perm_name": p[1]} for p in perm_res.all()]
        out.append(
            {
                "id": r.id,
                "role_code": r.role_code,
                "role_name": r.role_name,
                "status": r.status,
                "perms": perms,
            }
        )
    return out


async def create_role(db: AsyncSession, data: dict) -> SysRole:
    role = SysRole(
        role_code=data["role_code"],
        role_name=data.get("role_name", data["role_code"]),
        status=int(data.get("status", 1)),
    )
    db.add(role)
    await db.flush()
    return role


async def update_role(db: AsyncSession, role_id: int, data: dict) -> SysRole | None:
    role = await db.get(SysRole, role_id)
    if not role:
        return None
    if "role_name" in data:
        role.role_name = data["role_name"]
    if "status" in data:
        role.status = int(data["status"])
    await db.commit()
    await db.refresh(role)
    return role


async def delete_role(db: AsyncSession, role_id: int) -> bool:
    role = await db.get(SysRole, role_id)
    if not role:
        return False
    await db.delete(role)
    await db.commit()
    return True


async def set_role_perms(db: AsyncSession, role_id: int, perm_ids: list[int]) -> None:
    await db.execute(
        SysRolePerm.__table__.delete().where(SysRolePerm.role_id == role_id)
    )
    for pid in set(perm_ids or []):
        perm = await db.get(SysPermission, pid)
        if perm:
            db.add(SysRolePerm(role_id=role_id, perm_id=pid))
    await db.commit()


# ============ 权限 ============
async def list_permissions(db: AsyncSession) -> list[dict]:
    res = await db.execute(select(SysPermission).order_by(SysPermission.id.desc()))
    return [
        {
            "id": p.id,
            "perm_code": p.perm_code,
            "perm_name": p.perm_name,
            "resource": p.resource,
            "action": p.action,
            "parent_id": p.parent_id,
        }
        for p in res.scalars().all()
    ]


async def create_permission(db: AsyncSession, data: dict) -> SysPermission:
    perm = SysPermission(
        perm_code=data["perm_code"],
        perm_name=data.get("perm_name"),
        resource=data.get("resource"),
        action=data.get("action"),
        parent_id=data.get("parent_id"),
    )
    db.add(perm)
    await db.flush()
    return perm


async def update_permission(
    db: AsyncSession, perm_id: int, data: dict
) -> SysPermission | None:
    perm = await db.get(SysPermission, perm_id)
    if not perm:
        return None
    for k in ("perm_name", "resource", "action", "parent_id"):
        if k in data:
            setattr(perm, k, data[k])
    await db.commit()
    await db.refresh(perm)
    return perm


async def delete_permission(db: AsyncSession, perm_id: int) -> bool:
    perm = await db.get(SysPermission, perm_id)
    if not perm:
        return False
    await db.delete(perm)
    await db.commit()
    return True


# ============ 灰度发布 ============
async def list_gray_releases(db: AsyncSession) -> list[dict]:
    res = await db.execute(select(ClientGrayRelease).order_by(ClientGrayRelease.id.desc()))
    return [
        {
            "id": g.id,
            "version_code": g.version_code,
            "enable": g.enable,
            "user_filter": g.user_filter,
        }
        for g in res.scalars().all()
    ]


async def create_gray_release(db: AsyncSession, data: dict) -> ClientGrayRelease:
    row = ClientGrayRelease(
        version_code=data.get("version_code"),
        enable=int(data.get("enable", 0)),
        user_filter=data.get("user_filter") or {},
    )
    db.add(row)
    await db.flush()
    return row


async def update_gray_release(
    db: AsyncSession, gray_id: int, data: dict
) -> ClientGrayRelease | None:
    row = await db.get(ClientGrayRelease, gray_id)
    if not row:
        return None
    if "version_code" in data:
        row.version_code = data["version_code"]
    if "enable" in data:
        row.enable = int(data["enable"])
    if "user_filter" in data:
        row.user_filter = data["user_filter"] or {}
    await db.commit()
    await db.refresh(row)
    return row


async def delete_gray_release(db: AsyncSession, gray_id: int) -> bool:
    row = await db.get(ClientGrayRelease, gray_id)
    if not row:
        return False
    await db.delete(row)
    await db.commit()
    return True
