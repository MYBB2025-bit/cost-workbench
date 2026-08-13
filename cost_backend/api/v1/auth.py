"""认证路由：登录、当前用户、菜单（驱动前端动态路由）。"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user
from db.session import get_db
from service import auth_service

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login")
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await auth_service.authenticate(db, form.username, form.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    user.last_login_at = __import__("datetime").datetime.now()
    await db.commit()
    token = await auth_service.build_token(db, user)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
async def me(user=Depends(get_current_user)):
    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "real_name": user.get("real_name"),
        "roles": user.get("roles", []),
        "perms": user.get("perms", []),
    }


@router.get("/menu")
async def menu(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """返回菜单与权限，供前端按权限生成动态路由。"""
    perms = set(user.get("perms", []))
    menus = [
        {"path": "/dashboard", "name": "仪表盘", "perm": None},
        {"path": "/project", "name": "工程项目", "perm": "project:view"},
        {"path": "/progress", "name": "进度款审核", "perm": "progress:view"},
        {"path": "/pricing", "name": "核价库", "perm": "pricing:view"},
        {"path": "/budget", "name": "预算清单", "perm": "budget:view"},
        {"path": "/change", "name": "变更签证", "perm": "change:view"},
        {"path": "/settlement", "name": "结算", "perm": "settlement:view"},
        {"path": "/risk", "name": "风险与预警", "perm": "risk:view"},
        {"path": "/ledger", "name": "最终资料台账", "perm": "ledger:view"},
        {"path": "/cost-dashboard", "name": "造价总览看板", "perm": "budget:view"},
        {"path": "/client/version-manage", "name": "客户端版本管理", "perm": "client:version:view"},
        {"path": "/system/users", "name": "用户管理", "perm": "user:view"},
        {"path": "/system/roles", "name": "角色管理", "perm": "role:view"},
        {"path": "/system/perms", "name": "权限管理", "perm": "perm:view"},
        {"path": "/system/gray", "name": "灰度发布", "perm": "client:gray:view"},
    ]
    accessible = [m for m in menus if (m["perm"] is None or m["perm"] in perms or "*" in perms)]
    return {
        "username": user["username"],
        "real_name": user.get("real_name"),
        "roles": user.get("roles", []),
        "perms": user.get("perms", []),
        "menus": accessible,
    }
