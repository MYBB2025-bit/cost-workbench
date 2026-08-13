"""Celery 应用实例（造价平台后台异步任务）。

- broker / result backend 默认复用 Redis（与缓存同源）。
- 任务代码集中在 `tasks.job_tasks`，在此显式导入以完成注册，
  同时保证 `celery -A celery_app.celery_app worker` 启动即可发现任务。
- 测试或无 broker 环境置 CELERY_TASK_ALWAYS_EAGER=true，任务本地同步执行。
"""
from celery import Celery

from core.config import settings

_broker = settings.CELERY_BROKER_URL or settings.REDIS_URL
_backend = settings.CELERY_RESULT_BACKEND or settings.REDIS_URL

celery_app = Celery(
    "cost_worker",
    broker=_broker,
    backend=_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=settings.CELERY_TASK_EAGER_PROPAGATES,
)

# 显式注册任务模块（避免 autodiscover 的隐式导入问题）
import tasks.job_tasks  # noqa: E402,F401
