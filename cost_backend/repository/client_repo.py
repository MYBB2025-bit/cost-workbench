"""客户端版本/补丁数据层。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ClientPatch, ClientVersion


async def list_versions(db: AsyncSession) -> list[ClientVersion]:
    res = await db.execute(select(ClientVersion).order_by(ClientVersion.publish_time.desc()))
    return list(res.scalars().all())


async def get_version(db: AsyncSession, version_code: str) -> ClientVersion | None:
    res = await db.execute(select(ClientVersion).where(ClientVersion.version_code == version_code))
    return res.scalar_one_or_none()


async def create_version(db: AsyncSession, data: dict) -> ClientVersion:
    v = ClientVersion(**data)
    db.add(v)
    await db.commit()
    await db.refresh(v)
    return v


async def list_patches(db: AsyncSession) -> list[ClientPatch]:
    res = await db.execute(select(ClientPatch).order_by(ClientPatch.id.desc()))
    return list(res.scalars().all())


async def create_patch(db: AsyncSession, data: dict) -> ClientPatch:
    p = ClientPatch(**data)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p
