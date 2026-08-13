"""后台异步任务：预算 Excel 导入 / 台账 CSV 导出。

设计要点：
- Celery 任务为同步函数，内部通过「独立线程 + 新事件循环」运行 async DB 操作，
  避免与 HTTP 请求所在事件循环冲突（eager 测试模式下同样安全）。
- 大文件不进消息队列：API 先把上传文件落到本地（或 MinIO）拿到路径/key，
  再把定位信息传给 worker，worker 自行读取并解析。
- 任务全程持有自己的 DB 会话，通过 TaskJob 记录进度与结果，前端轮询即可。
"""
import asyncio
import concurrent.futures
import csv
import io
import os
from collections.abc import Callable
from datetime import datetime

from celery_app import celery_app
from core.config import settings
from db.session import SessionLocal
from repository import task_repo
from service import budget_service, ledger_service, migration_service
from utils.xlsx_import import parse_budget_xlsx


def _run_async(coro_factory: Callable[[], object]) -> object:
    """在独立线程中运行 async 协程，规避当前线程已有事件循环的问题。"""

    def _runner() -> object:
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro_factory())
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(_runner).result()


# ===================== 预算导入 =====================
@celery_app.task(name="import_budget_task")
def import_budget_task(job_uuid: str, storage_path: str, project_id: int, user_id: int):
    return _run_async(lambda: _import_job(job_uuid, storage_path, project_id, user_id))


async def _import_job(job_uuid: str, storage_path: str, project_id: int, user_id: int):
    async with SessionLocal() as db:
        job = await task_repo.get_by_uuid(db, job_uuid)
        if not job:
            return None
        job.status = "running"
        job.started_at = datetime.now()
        await db.commit()
        try:
            with open(storage_path, "rb") as f:
                content = f.read()
            rows = parse_budget_xlsx(content)
            job.total = len(rows)
            await db.commit()

            stats = await budget_service.bulk_import(db, project_id, rows, user_id)
            job.status = "success"
            job.finished_at = datetime.now()
            job.result = stats
            job.processed = job.total
            job.progress = 100
            await db.commit()
            return stats
        except Exception as e:  # noqa: BLE001
            job.status = "failed"
            job.error = str(e)
            job.finished_at = datetime.now()
            await db.commit()
            raise
        finally:
            try:
                os.remove(storage_path)
            except OSError:
                pass


# ===================== 台账导出 =====================
@celery_app.task(name="export_ledger_task")
def export_ledger_task(job_uuid: str, project_id, user_id: int, project_ids):
    return _run_async(lambda: _export_job(job_uuid, project_id, user_id, project_ids))


async def _export_job(job_uuid: str, project_id, user_id: int, project_ids):
    async with SessionLocal() as db:
        job = await task_repo.get_by_uuid(db, job_uuid)
        if not job:
            return None
        job.status = "running"
        job.started_at = datetime.now()
        await db.commit()
        try:
            # project_ids 为 None 表示超级管理员可访问全部项目
            pids = list(project_ids) if project_ids else None
            rows = await ledger_service.export_ledger(db, pids, project_id)

            headers = ["项目名称", "类别", "资料名称", "负责人", "截止", "状态", "完成时间"]
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(headers)
            for r in rows:
                writer.writerow([
                    r["project_name"], r["category"], r["name"],
                    r["owner"], r["due"], r["status"], r["finished_at"],
                ])

            out_dir = os.path.join(settings.LOCAL_UPLOAD_DIR, "exports")
            os.makedirs(out_dir, exist_ok=True)
            fname = f"ledger_{job_uuid}.csv"
            fpath = os.path.join(out_dir, fname)
            # utf-8-sig 写入 BOM，Excel 直接打开不乱码
            with open(fpath, "w", encoding="utf-8-sig") as f:
                f.write(buf.getvalue())

            job.status = "success"
            job.finished_at = datetime.now()
            job.progress = 100
            job.processed = job.total or 1
            job.result = {"file_path": fpath, "filename": fname, "count": len(rows)}
            await db.commit()
            return job.result
        except Exception as e:  # noqa: BLE001
            job.status = "failed"
            job.error = str(e)
            job.finished_at = datetime.now()
            await db.commit()
            raise


# ===================== 历史数据迁移 =====================
@celery_app.task(name="migrate_user_data_task")
def migrate_user_data_task(job_uuid: str, file_path: str, user_id: int):
    return _run_async(lambda: _migrate_job(job_uuid, file_path, user_id))


async def _migrate_job(job_uuid: str, file_path: str, user_id: int):
    async with SessionLocal() as db:
        job = await task_repo.get_by_uuid(db, job_uuid)
        if not job:
            return None
        try:
            stats = await migration_service.run_migration(db, job, user_id, file_path)
            return stats
        except Exception as e:  # noqa: BLE001
            job.status = "failed"
            job.error = str(e)
            job.finished_at = datetime.now()
            await db.commit()
            raise

