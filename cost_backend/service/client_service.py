"""客户端更新服务：版本检测 + 灰度判断 + 差分补丁流式返回。
适配说明：原示例直接使用 Minio 客户端；此处通过 utils.storage 抽象，
在 MinIO 不可用时自动降级本地文件（保证开发/沙箱可测，生产走 MinIO）。
"""
import json

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db.models import ClientGrayRelease, ClientPatch, ClientVersion
from utils.storage import storage


async def check_version(db: AsyncSession, local_ver: str, user_id: int = None) -> dict:
    """客户端版本检测 + 灰度判断 + 差分补丁推荐。"""
    stmt = (
        select(ClientVersion)
        .where(ClientVersion.status == 1)
        .order_by(ClientVersion.publish_time.desc())
    )
    latest_ver: ClientVersion = (await db.execute(stmt)).scalar_one_or_none()
    if not latest_ver:
        return {"update": False}

    # 灰度：开启灰度时需校验用户白名单
    gray_stmt = select(ClientGrayRelease).where(
        ClientGrayRelease.version_code == latest_ver.version_code,
        ClientGrayRelease.enable == 1,
    )
    gray_row = (await db.execute(gray_stmt)).scalar_one_or_none()
    if gray_row:
        filter_cfg = gray_row.user_filter or {}
        if isinstance(filter_cfg, str):
            filter_cfg = json.loads(filter_cfg or "{}")
        white_user_list = filter_cfg.get("user_ids", []) if isinstance(filter_cfg, dict) else []
        if user_id and int(user_id) not in [int(x) for x in white_user_list]:
            return {"update": False}

    if local_ver == latest_ver.version_code:
        return {"update": False}

    # 查询【本地版本→最新版本】的 bsdiff 补丁
    patch_stmt = select(ClientPatch).where(
        ClientPatch.from_version == local_ver,
        ClientPatch.to_version == latest_ver.version_code,
        ClientPatch.status == 1,
    )
    patch = (await db.execute(patch_stmt)).scalar_one_or_none()

    resp = {
        "update": True,
        "latest_version": latest_ver.version_code,
        "force_update": bool(latest_ver.force_update),
        "min_compat_version": latest_ver.min_compat_version,
        "version_desc": latest_ver.version_desc,
    }
    if patch:
        resp["patch"] = {
            "patch_id": patch.id,
            "md5": patch.patch_md5,
            "size": patch.patch_size,
        }
    else:
        resp["patch"] = None
        # 无差分补丁时，若已上传整包则告知客户端整包下载地址（兜底更新）
        if latest_ver.full_pkg_minio_path:
            resp["download_url"] = f"/client/version/download/{latest_ver.version_code}"
            resp["full_md5"] = latest_ver.full_pkg_md5
    return resp


async def get_patch_stream(db: AsyncSession, patch_id: int) -> tuple[object, int]:
    """获取补丁流式迭代器与大小，供 Range 断点续传使用。"""
    stmt = select(ClientPatch).where(ClientPatch.id == patch_id, ClientPatch.status == 1)
    patch = (await db.execute(stmt)).scalar_one_or_none()
    if not patch:
        raise HTTPException(status_code=404, detail="补丁不存在")

    try:
        stream_iter, size = storage.get_object_stream(
            settings.MINIO_BUCKET_PATCH, patch.patch_minio_path
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="补丁文件不存在（存储缺失）")

    return stream_iter, size
