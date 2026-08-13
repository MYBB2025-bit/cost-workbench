"""异步数据库会话与初始化。"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import settings

engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    """建表（开发/降级用；生产使用 migrations/001_init.sql）。"""
    from db import models  # noqa: F401  确保模型注册

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# 便于在其他模块导入 Base
from db.base import Base  # noqa: E402
