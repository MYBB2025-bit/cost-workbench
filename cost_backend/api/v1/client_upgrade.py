"""客户端更新路由（重点）：版本检测 / 补丁下载 / 版本发布 / 补丁上传。"""
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.deps import get_current_user, require_perm
from db.session import get_db
from repository import client_repo
from service import client_service
from utils.md5 import calc_md5_file
from utils.storage import storage

router = APIRouter(prefix="/client", tags=["客户端更新"])


def _parse_range(header: str, total: int):
    """解析 HTTP Range 头，返回 (start, end) 或 None。"""
    if not header or not header.lower().startswith("bytes="):
        return None
    spec = header[len("bytes="):].strip()
    parts = spec.split("-")
    if len(parts) != 2:
        return None
    start_s, end_s = parts
    if not start_s:
        # 后缀形式 bytes=-N：取最后 N 字节
        if not end_s:
            return None
        suffix = int(end_s)
        start = max(0, total - suffix)
        end = total - 1
    else:
        start = int(start_s)
        end = int(end_s) if end_s else total - 1
    if end >= total:
        end = total - 1
    if start < 0 or start > end:
        return None
    return start, end


def _slice_stream(stream_iter, start: int, end: int):
    """从流中跳过前 start 字节，并最多产出 (end - start + 1) 字节。"""
    remaining_skip = start
    while remaining_skip > 0:
        chunk = next(stream_iter, b"")
        if not chunk:
            return
        if len(chunk) <= remaining_skip:
            remaining_skip -= len(chunk)
            continue
        chunk = chunk[remaining_skip:]
        remaining_skip = 0
        yield chunk
    budget = end - start + 1
    for chunk in stream_iter:
        if not chunk:
            break
        if len(chunk) <= budget:
            budget -= len(chunk)
            yield chunk
        else:
            yield chunk[:budget]
            return


def _stream_with_range(stream_iter, total: int, request: Request, filename: str):
    """根据 Range 头返回 206 部分流或 200 全量流。"""
    parsed = _parse_range(request.headers.get("Range"), total)
    if parsed:
        start, end = parsed
        body = _slice_stream(stream_iter, start, end)
        headers = {
            "Content-Range": f"bytes {start}-{end}/{total}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(end - start + 1),
            "Content-Disposition": f'attachment; filename="{filename}"',
        }
        return StreamingResponse(body, status_code=206, media_type="application/octet-stream", headers=headers)
    return StreamingResponse(
        stream_iter,
        media_type="application/octet-stream",
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(total),
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/version/check")
async def api_check_version(local_ver: str, db: AsyncSession = Depends(get_db),
                            user=Depends(get_current_user)):
    user_id = user.get("user_id")
    return await client_service.check_version(db, local_ver, user_id=user_id)


@router.get("/patch/download/{patch_id}")
async def api_download_patch(patch_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    stream_iter, size = await client_service.get_patch_stream(db, patch_id)
    filename = f"patch_{patch_id}.bsdiff"
    return _stream_with_range(stream_iter, size, request, filename)


@router.get("/version/download/{version_code}")
async def api_download_full_version(version_code: str, request: Request, db: AsyncSession = Depends(get_db)):
    """下载整包（无差分补丁时的兜底更新包）。免鉴权，与补丁下载一致。"""
    from sqlalchemy import select

    from db.models import ClientVersion
    ver = (await db.execute(
        select(ClientVersion).where(ClientVersion.version_code == version_code)
    )).scalar_one_or_none()
    if not ver or not ver.full_pkg_minio_path:
        raise HTTPException(status_code=404, detail="该版本未提供整包下载")
    try:
        stream_iter, size = storage.get_object_stream(settings.MINIO_BUCKET_PATCH, ver.full_pkg_minio_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="整包文件不存在（存储缺失）")
    filename = f"{version_code}.exe"
    return _stream_with_range(stream_iter, size, request, filename)


@router.post("/version/publish", dependencies=[Depends(require_perm("client:version:publish"))])
async def publish_version(body: dict, db: AsyncSession = Depends(get_db)):
    """发布新版本（管理员）。body: {version_code, version_desc, force_update, min_compat_version}。"""
    code = body.get("version_code")
    if not code:
        raise HTTPException(status_code=400, detail="缺少 version_code")
    exists = await client_repo.get_version(db, code)
    if exists:
        raise HTTPException(status_code=400, detail="版本号已存在")
    row = await client_repo.create_version(db, {
        "version_code": code,
        "version_desc": body.get("version_desc"),
        "force_update": int(bool(body.get("force_update", False))),
        "min_compat_version": body.get("min_compat_version"),
        "status": 1,
    })
    return {"id": row.id, "version_code": row.version_code}


@router.post("/patch/upload", dependencies=[Depends(require_perm("client:patch:upload"))])
async def upload_patch(
    file: UploadFile = File(...),
    from_version: str = Query(""),
    to_version: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    """上传 bsdiff 补丁文件，记录元数据（md5/大小）。"""
    import os
    import tempfile
    if not from_version or not to_version:
        raise HTTPException(status_code=400, detail="需提供 from_version 与 to_version")
    suffix = os.path.splitext(file.filename or "patch.bsdiff")[1] or ".bsdiff"
    key = f"{from_version}__to__{to_version}{suffix}"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
    size = os.path.getsize(tmp.name)
    md5 = calc_md5_file(tmp.name)
    with open(tmp.name, "rb") as f:
        storage.put_object(settings.MINIO_BUCKET_PATCH, key, f, length=size)
    os.remove(tmp.name)
    row = await client_repo.create_patch(db, {
        "from_version": from_version,
        "to_version": to_version,
        "patch_minio_path": key,
        "patch_md5": md5,
        "patch_size": size,
        "status": 1,
    })
    return {"id": row.id, "md5": md5, "size": size}


@router.get("/version/list")
async def version_list(db: AsyncSession = Depends(get_db)):
    return await client_repo.list_versions(db)


@router.get("/patch/list")
async def patch_list(db: AsyncSession = Depends(get_db)):
    return await client_repo.list_patches(db)
