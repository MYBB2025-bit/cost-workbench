"""历史数据迁移测试：用小型合成 JSON 验证迁移管道与 API 权限。

不加载真实 184MB 文件（避免测试过重），但结构与真实文件一致，
含一个 base64 内嵌附件，验证「附件解码 → 对象存储 → CostAttachment」链路。
"""
import base64
import json
import os

import pytest

API = "/api/v1"


def _login(client, username, password):
    r = client.post(f"{API}/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _make_fixture(tmp_path) -> str:
    """构造一个与真实 user-data.json 同构的小型 JSON（含 base64 附件）。"""
    sample = b"PK\x03\x04 fake zip content for migration test"
    b64 = base64.b64encode(sample).decode()
    data = {
        "projects": [
            {"id": "p1", "name": "示范项目A", "type": "construction",
             "budgetAmount": "1000000", "estimateAmount": "1200000"},
        ],
        "settlements": [
            {"id": "s1", "projectId": "p1", "name": "1#楼结算",
             "status": "在办", "auditStatus": "已审", "amount": 500000},
        ],
        "svRecords": [
            {"id": "v1", "code": "QZ-001", "name": "基础签证", "submitDate": "2026-01-10",
             "note": "土方签证", "summary": "现场确认", "ready": True, "reviewStatus": "已签",
             "files": [{"id": "f1", "name": "签证附件.pdf", "size": len(sample),
                        "hash": "abc123", "data": f"data:application/pdf;base64,{b64}"}]},
        ],
        "payments": [],
        "checklists": {
            "p1": {"name": "资料台账", "items": [
                {"id": "d1", "name": "联系单", "stage": "过程", "checked": True, "files": []},
                {"id": "d2", "name": "工程签证", "stage": "过程", "checked": False, "files": []},
            ]},
        },
        "contacts": [
            {"id": "c1", "name": "张三", "role": "业主", "title": "经理", "phone": "13800000000"},
        ],
        "tasks": [
            {"id": "t1", "title": "进度款申请", "type": "payment", "status": "在办",
             "amount": 300000, "due": "2026-02-01", "contact": "李四", "risk": False,
             "summary": "2月进度"},
        ],
        "pricings": [],
    }
    path = os.path.join(str(tmp_path), "user-data.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return path


def test_migration_full_pipeline(client, tmp_path, monkeypatch):
    """跑通迁移：结构化落库 + 附件落存储 + job success + 进度 100。"""
    path = _make_fixture(tmp_path)
    # 将迁移源指向合成小文件（避免加载真实 184MB 文件）
    monkeypatch.setattr("core.config.settings.MIGRATION_DATA_PATH", path)
    token = _login(client, "admin", "admin123")
    h = {"Authorization": f"Bearer {token}"}

    # 触发迁移（eager 模式同步完成）
    r = client.post(f"{API}/migration/run", headers=h)
    assert r.status_code == 200, r.text
    job_id = r.json()["job_id"]

    # 查询作业状态
    rj = client.get(f"{API}/task/{job_id}", headers=h)
    assert rj.status_code == 200, rj.text
    job = rj.json()
    assert job["status"] == "success", job
    assert job["progress"] == 100
    stats = job["result"]
    assert stats["projects"] == 1
    assert stats["settlements"] == 1
    assert stats["visas"] == 1
    assert stats["attachments"] == 1
    assert stats["ledger_docs"] == 2
    assert stats["progress_payments"] == 1
    assert stats["contacts_cataloged"] == 1

    # 附件确实落到了对象存储（本地模式即文件系统），内容可还原
    import asyncio

    # 通过 DB 取 attachment 的 storage_key
    from sqlalchemy import select

    from core.config import settings
    from db.session import SessionLocal
    from utils.storage import storage
    async def _get():
        async with SessionLocal() as db:
            from db.models import (
                CostAttachment,
                CostLedgerDoc,
                CostProgressPayment,
                CostProject,
                CostSettlement,
                CostVisa,
            )
            n_proj = (await db.execute(select(CostProject))).scalars().all()
            n_set = (await db.execute(select(CostSettlement))).scalars().all()
            n_visa = (await db.execute(select(CostVisa))).scalars().all()
            n_led = (await db.execute(select(CostLedgerDoc))).scalars().all()
            n_pay = (await db.execute(select(CostProgressPayment))).scalars().all()
            att = (await db.execute(select(CostAttachment))).scalars().first()
            return (len(n_proj), len(n_set), len(n_visa), len(n_led), len(n_pay), att)
    n_proj, n_set, n_visa, n_led, n_pay, att = asyncio.run(_get())

    assert n_proj == 1 and n_set == 1 and n_visa == 1 and n_led == 2 and n_pay == 1
    assert att is not None
    assert att.owner_type == "visa" and att.filename == "签证附件.pdf"
    # 校验存储中的文件内容等于原始 base64 解码结果
    stream, size = storage.get_object_stream(settings.MINIO_BUCKET_ATTACH, att.storage_key)
    got = b"".join(stream)
    assert got == b"PK\x03\x04 fake zip content for migration test"
    assert size == att.size


def test_migration_run_requires_super(client, seed_data):
    """非超管（受限用户）调用迁移应被 403 拒绝。"""
    token = _login(client, "editor", "editor123")
    h = {"Authorization": f"Bearer {token}"}
    r = client.post(f"{API}/migration/run", headers=h)
    assert r.status_code == 403, r.text


def test_migration_preview(client):
    """预览接口返回文件体积与计数（用真实 184MB 文件，只读不写库）。

    CI 环境未提交 184MB 真实数据文件时自动跳过，避免在无 fixtures 时失败。
    """
    from core.config import settings

    path = settings.MIGRATION_DATA_PATH
    if not os.path.isfile(path):
        pytest.skip(f"migration data file not found: {path}")
    size = os.path.getsize(path)
    if size < 100_000_000:
        pytest.skip(f"migration data file too small for preview assertion: {size} bytes")

    token = _login(client, "admin", "admin123")
    h = {"Authorization": f"Bearer {token}"}
    r = client.get(f"{API}/migration/preview", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["file_size_bytes"] > 100_000_000  # 真实文件约 184MB
    counts = body["counts"]
    assert counts["projects"] >= 1
    assert counts["svRecords"] >= 1
