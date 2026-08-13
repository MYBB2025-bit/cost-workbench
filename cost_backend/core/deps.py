"""权限依赖：RBAC 功能权限 + 造价数据权限（项目级隔离）。
JWT payload 约定字段：
- user_id: int
- username: str
- perms: List[str]   角色聚合的功能权限码
- roles: List[str]   角色码
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import verify_token
from db.session import get_db
from service.auth_service import get_user_permission_projects

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    payload = verify_token(token)
    if not payload or "user_id" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token无效或已过期")
    return payload


def require_perm(perm_code: str):
    """按钮/接口功能权限校验依赖工厂。"""

    async def _dep(user=Depends(get_current_user)):
        perms = user.get("perms") or []
        # 超级管理员放行所有
        if "*" in perms or "super:all" in perms:
            return user
        if perm_code not in perms:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"无操作权限：{perm_code}")
        return user

    return _dep


async def get_user_project_ids(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list:
    """【造价独有】获取当前用户可访问的项目ID列表，实现数据自动隔离。"""
    return await get_user_permission_projects(db, user["user_id"])
