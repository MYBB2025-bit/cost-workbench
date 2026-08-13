"""测试配置：使用 SQLite 文件库（降级模式），TestClient 触发 lifespan 自动建表+初始管理员。"""
import asyncio
import os

# 必须在导入 app 前设置环境变量
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_cost.db"
os.environ["USE_LOCAL_STORAGE"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["INIT_ADMIN_USERNAME"] = "admin"
os.environ["INIT_ADMIN_PASSWORD"] = "admin123"
os.environ["MINIO_BUCKET_PATCH"] = "cost-patch"
# 测试环境：Celery 任务本地同步执行，无需 Redis broker
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "1"
os.environ["CELERY_TASK_EAGER_PROPAGATES"] = "1"

import pytest
from fastapi.testclient import TestClient

from core.security import get_password_hash
from db import models  # noqa: F401
from db.models import CostProject, SysUser, SysUserProjectPerm
from db.session import SessionLocal, engine
from main import app
from service import auth_service


@pytest.fixture(scope="function")
def client():
    # 每次测试重建表，保证隔离
    asyncio.run(_reset_db())
    with TestClient(app) as c:  # 触发 lifespan：建表 + 初始管理员
        yield c


async def _reset_db():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.drop_all)
        await conn.run_sync(models.Base.metadata.create_all)
    async with SessionLocal() as db:
        await auth_service.init_admin(db)


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture()
def seed_data():
    """创建测试项目与受限用户（仅可见该项目）。"""

    async def _seed():
        async with SessionLocal() as db:
            proj = CostProject(project_name="示范项目A", project_code="P-001", contract_amount=1000000, status="active")
            db.add(proj)
            await db.flush()
            # 受限用户
            u = SysUser(username="editor", real_name="编辑员", password_hash=get_password_hash("editor123"), status=1)
            db.add(u)
            await db.flush()
            db.add(SysUserProjectPerm(user_id=u.id, project_id=proj.id))
            await db.commit()
            return {"project_id": proj.id, "user_id": u.id}

    return _run(_seed())
