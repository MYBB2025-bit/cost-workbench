"""系统管理路由：用户、角色、权限、灰度发布、项目数据权限分配。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import require_perm
from db.session import get_db
from repository import project_repo
from service import system_service

router = APIRouter(prefix="/system", tags=["系统管理"])


# ============ 用户 ============
@router.get("/users", dependencies=[Depends(require_perm("user:view"))])
async def list_users(db: AsyncSession = Depends(get_db)):
    return await system_service.list_users(db)


@router.post("/users", dependencies=[Depends(require_perm("user:edit"))])
async def create_user(body: dict, db: AsyncSession = Depends(get_db)):
    if not body.get("username"):
        raise HTTPException(status_code=400, detail="用户名不能为空")
    user = await system_service.create_user(db, body)
    if body.get("role_ids"):
        await system_service.set_user_roles(db, user.id, body["role_ids"])
    if body.get("project_ids"):
        await system_service.set_user_projects(db, user.id, body["project_ids"])
    await db.commit()
    return {"id": user.id, "username": user.username}


@router.put("/users/{user_id}", dependencies=[Depends(require_perm("user:edit"))])
async def update_user(user_id: int, body: dict, db: AsyncSession = Depends(get_db)):
    user = await system_service.update_user(db, user_id, body)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if "role_ids" in body:
        await system_service.set_user_roles(db, user_id, body["role_ids"])
    if "project_ids" in body:
        await system_service.set_user_projects(db, user_id, body["project_ids"])
    return {"id": user.id}


@router.delete("/users/{user_id}", dependencies=[Depends(require_perm("user:edit"))])
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    ok = await system_service.delete_user(db, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"ok": True}


# ============ 角色 ============
@router.get("/roles", dependencies=[Depends(require_perm("role:view"))])
async def list_roles(db: AsyncSession = Depends(get_db)):
    return await system_service.list_roles(db)


@router.post("/roles", dependencies=[Depends(require_perm("role:edit"))])
async def create_role(body: dict, db: AsyncSession = Depends(get_db)):
    if not body.get("role_code"):
        raise HTTPException(status_code=400, detail="角色编码不能为空")
    role = await system_service.create_role(db, body)
    if body.get("perm_ids"):
        await system_service.set_role_perms(db, role.id, body["perm_ids"])
    await db.commit()
    return {"id": role.id, "role_code": role.role_code}


@router.put("/roles/{role_id}", dependencies=[Depends(require_perm("role:edit"))])
async def update_role(role_id: int, body: dict, db: AsyncSession = Depends(get_db)):
    role = await system_service.update_role(db, role_id, body)
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    if "perm_ids" in body:
        await system_service.set_role_perms(db, role_id, body["perm_ids"])
    return {"id": role.id}


@router.delete("/roles/{role_id}", dependencies=[Depends(require_perm("role:edit"))])
async def delete_role(role_id: int, db: AsyncSession = Depends(get_db)):
    ok = await system_service.delete_role(db, role_id)
    if not ok:
        raise HTTPException(status_code=404, detail="角色不存在")
    return {"ok": True}


# ============ 权限 ============
@router.get("/permissions", dependencies=[Depends(require_perm("perm:view"))])
async def list_permissions(db: AsyncSession = Depends(get_db)):
    return await system_service.list_permissions(db)


@router.post("/permissions", dependencies=[Depends(require_perm("perm:edit"))])
async def create_permission(body: dict, db: AsyncSession = Depends(get_db)):
    if not body.get("perm_code"):
        raise HTTPException(status_code=400, detail="权限编码不能为空")
    perm = await system_service.create_permission(db, body)
    await db.commit()
    return {"id": perm.id, "perm_code": perm.perm_code}


@router.put("/permissions/{perm_id}", dependencies=[Depends(require_perm("perm:edit"))])
async def update_permission(perm_id: int, body: dict, db: AsyncSession = Depends(get_db)):
    perm = await system_service.update_permission(db, perm_id, body)
    if not perm:
        raise HTTPException(status_code=404, detail="权限不存在")
    return {"id": perm.id}


@router.delete("/permissions/{perm_id}", dependencies=[Depends(require_perm("perm:edit"))])
async def delete_permission(perm_id: int, db: AsyncSession = Depends(get_db)):
    ok = await system_service.delete_permission(db, perm_id)
    if not ok:
        raise HTTPException(status_code=404, detail="权限不存在")
    return {"ok": True}


# ============ 灰度发布 ============
@router.get("/gray-releases", dependencies=[Depends(require_perm("client:gray:view"))])
async def list_gray_releases(db: AsyncSession = Depends(get_db)):
    return await system_service.list_gray_releases(db)


@router.post("/gray-releases", dependencies=[Depends(require_perm("client:gray:edit"))])
async def create_gray_release(body: dict, db: AsyncSession = Depends(get_db)):
    row = await system_service.create_gray_release(db, body)
    await db.commit()
    return {"id": row.id, "version_code": row.version_code}


@router.put("/gray-releases/{gray_id}", dependencies=[Depends(require_perm("client:gray:edit"))])
async def update_gray_release(gray_id: int, body: dict, db: AsyncSession = Depends(get_db)):
    row = await system_service.update_gray_release(db, gray_id, body)
    if not row:
        raise HTTPException(status_code=404, detail="灰度配置不存在")
    return {"id": row.id}


@router.delete("/gray-releases/{gray_id}", dependencies=[Depends(require_perm("client:gray:edit"))])
async def delete_gray_release(gray_id: int, db: AsyncSession = Depends(get_db)):
    ok = await system_service.delete_gray_release(db, gray_id)
    if not ok:
        raise HTTPException(status_code=404, detail="灰度配置不存在")
    return {"ok": True}


# ============ 项目选择（给用户分配数据权限） ============
@router.get("/projects", dependencies=[Depends(require_perm("user:view"))])
async def list_projects_for_select(db: AsyncSession = Depends(get_db)):
    rows = await project_repo.list_projects(db)
    return [
        {"id": p.id, "project_name": p.project_name, "project_code": p.project_code}
        for p in rows
    ]
