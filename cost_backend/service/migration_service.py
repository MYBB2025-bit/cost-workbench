"""历史业务数据迁移：把旧版单文件应用导出的 user-data.json 入库。

要点：
- 结构化记录（项目/结算/签证/台账/进度款）按字段映射写入新库模型。
- 「重量级」附件（svRecords.files[].data 为 base64 内嵌，单文件可达 144MB）
  不走 DB 文本列，而是 base64 解码后写入对象存储（MinIO/本地），只保留
  CostAttachment 元数据（路径/大小/哈希）。
- 全程通过 TaskJob 记录进度（total/processed/progress），前端轮询即可。
- 整个 184MB JSON 在 worker 内一次解析（环境已验证可承载），附件解码为
  二进制后直接落存储，不做二次内存拷贝。
"""
import base64
import io
import json
import os
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db.models import (
    CostAttachment,
    CostLedgerDoc,
    CostProgressPayment,
    CostProject,
    CostSettlement,
    CostVisa,
)
from utils.storage import storage


def _to_float(v: Any, default: float = 0.0) -> float:
    """把空字符串/None/数字统一成 float。"""
    if v is None or v == "":
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _extract_b64(data_uri: str) -> tuple[bytes, str]:
    """从 data:...;base64,XXXX 中抽取原始字节，返回 (raw, mime)。"""
    if "," not in data_uri:
        # 纯 base64（无 data URI 前缀）
        return base64.b64decode(data_uri), "application/octet-stream"
    header, b64 = data_uri.split(",", 1)
    mime = "application/octet-stream"
    if header.startswith("data:") and ";" in header:
        mime = header[5:].split(";", 1)[0] or mime
    return base64.b64decode(b64), mime


async def run_migration(db: AsyncSession, job, user_id: int, file_path: str) -> dict:
    """执行一次完整迁移，返回汇总字典。"""
    job.status = "running"
    job.started_at = datetime.now()
    await db.commit()

    with open(file_path, encoding="utf-8") as f:
        raw = json.load(f)

    projects = raw.get("projects") or []
    settlements = raw.get("settlements") or []
    sv_records = raw.get("svRecords") or []
    checklists = raw.get("checklists") or {}
    tasks = raw.get("tasks") or []
    contacts = raw.get("contacts") or []

    # 台账条目展开（checklists 是 {projectId: {name, items:[...]}}）
    ledger_items: list[dict] = []
    for pid, cl in checklists.items():
        for it in (cl.get("items") or []):
            ledger_items.append({"project_key": pid, **it})

    total = (
        len(projects) + len(settlements) + len(sv_records)
        + len(ledger_items) + len(tasks)
    )
    job.total = total
    await db.commit()

    stats = {
        "projects": 0, "settlements": 0, "visas": 0,
        "attachments": 0, "ledger_docs": 0, "progress_payments": 0,
        "contacts_cataloged": len(contacts),
    }
    legacy_to_new: dict[str, int] = {}

    # ---- 项目 ----
    for p in projects:
        proj = CostProject(
            project_code=p.get("id"),
            project_name=p.get("name") or "未命名项目",
            contract_amount=_to_float(p.get("budgetAmount") or p.get("estimateAmount")),
            status="active",
        )
        db.add(proj)
        await db.flush()
        legacy_to_new[p.get("id")] = proj.id
        stats["projects"] += 1
        job.processed += 1
        job.progress = int(job.processed / total * 100) if total else 100
        await db.commit()

    # 无 projectId 的实体（签证/任务）统一挂到首个项目，便于查询
    default_project_id = next(iter(legacy_to_new.values()), None)

    # ---- 结算单 ----
    for s in settlements:
        pid = legacy_to_new.get(s.get("projectId"), default_project_id)
        db.add(CostSettlement(
            project_id=pid,
            settlement_no=s.get("id"),
            settlement_name=s.get("name"),
            total_amount=_to_float(s.get("amount")),
            status=s.get("auditStatus") or s.get("status"),
            creator=user_id,
        ))
        stats["settlements"] += 1
        job.processed += 1
        job.progress = int(job.processed / total * 100) if total else 100
        await db.commit()

    # ---- 签证单 + 附件抽取 ----
    for sv in sv_records:
        pid = legacy_to_new.get(sv.get("projectId"), default_project_id)
        content = "\n".join(filter(None, [sv.get("note"), sv.get("summary")])).strip()
        visa = CostVisa(
            project_id=pid,
            visa_no=sv.get("code"),
            visa_date=sv.get("submitDate"),
            content=content or None,
            amount=0,
            status=sv.get("reviewStatus") or ("done" if sv.get("ready") else "draft"),
            creator=user_id,
        )
        db.add(visa)
        await db.flush()
        stats["visas"] += 1

        # 抽取内嵌附件（base64 → 对象存储）
        for f in (sv.get("files") or []):
            data_uri = f.get("data")
            if not data_uri:
                continue
            raw_bytes, _mime = _extract_b64(data_uri)
            fname = f.get("name") or "attachment.bin"
            fhash = f.get("hash") or "unknown"
            key = f"visa/{visa.id}/{fhash}_{fname}"
            storage.put_object(
                settings.MINIO_BUCKET_ATTACH, key, io.BytesIO(raw_bytes), len(raw_bytes)
            )
            db.add(CostAttachment(
                owner_type="visa",
                owner_id=visa.id,
                filename=fname,
                storage_key=key,
                size=int(f.get("size") or len(raw_bytes)),
                md5=fhash,
                uploaded_by=user_id,
            ))
            stats["attachments"] += 1

        job.processed += 1
        job.progress = int(job.processed / total * 100) if total else 100
        await db.commit()

    # ---- 最终资料台账 ----
    for it in ledger_items:
        db.add(CostLedgerDoc(
            project_id=legacy_to_new.get(it.get("project_key"), default_project_id),
            category=it.get("stage"),
            name=it.get("name"),
            status="done" if it.get("checked") else "pending",
        ))
        stats["ledger_docs"] += 1
        job.processed += 1
        job.progress = int(job.processed / total * 100) if total else 100
        await db.commit()

    # ---- 任务/进度款 ----
    for t in tasks:
        db.add(CostProgressPayment(
            project_id=default_project_id,
            period_name=t.get("title"),
            apply_amount=_to_float(t.get("amount")),
            status=t.get("status"),
            creator=user_id,
        ))
        stats["progress_payments"] += 1
        job.processed += 1
        job.progress = int(job.processed / total * 100) if total else 100
        await db.commit()

    job.status = "success"
    job.finished_at = datetime.now()
    job.progress = 100
    job.processed = total
    job.result = stats
    await db.commit()
    return stats


async def preview_user_data(file_path: str) -> dict:
    """只读预览：文件体积 + 各实体计数（不写库）。"""
    size = os.path.getsize(file_path)
    with open(file_path, encoding="utf-8") as f:
        raw = json.load(f)
    return {
        "file_path": file_path,
        "file_size_bytes": size,
        "counts": {
            "projects": len(raw.get("projects") or []),
            "settlements": len(raw.get("settlements") or []),
            "svRecords": len(raw.get("svRecords") or []),
            "payments": len(raw.get("payments") or []),
            "checklists": len(raw.get("checklists") or {}),
            "contacts": len(raw.get("contacts") or []),
            "tasks": len(raw.get("tasks") or []),
            "pricings": len(raw.get("pricings") or []),
        },
    }


def get_migration_path() -> str:
    """解析迁移源文件路径（绝对或相对 backend 工作目录）。"""
    p = settings.MIGRATION_DATA_PATH
    return p if os.path.isabs(p) else os.path.join(os.getcwd(), p)
