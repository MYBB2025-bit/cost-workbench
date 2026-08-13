"""日志配置：结构化 JSON 日志 + 可选 Loki 投递。

两种聚合路径（可并存，但通常二选一以避免重复采集）：
1. Promtail 抓取容器 stdout（docker json-file）→ 经典方案，无需改动应用代码。
2. 应用内 LokiHandler 直接 push 结构化日志（LOKI_ENABLED=true），适合无法挂载
   docker.sock 的环境（如某些托管/K8s 场景）。
"""
import json
import logging
import queue
import sys
import threading
from datetime import UTC, datetime

import requests

from core.config import settings

try:
    import contextvars

    _request_id_var = contextvars.ContextVar("cost_request_id", default="-")
except Exception:  # pragma: no cover - 极老环境降级
    import threading as _threading

    _local = _threading.local()

    class _FallbackVar:
        def get(self):
            return getattr(_local, "rid", "-")

        def set(self, v):
            _local.rid = v

    _request_id_var = _FallbackVar()

# 对外暴露，供中间件事务设置/读取
request_id_var = _request_id_var


class JsonFormatter(logging.Formatter):
    """把日志记录序列化为单行 JSON，便于 Loki / Promtail 解析与检索。"""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            payload.update(extra)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)
        return json.dumps(payload, ensure_ascii=False)


class RequestIdFilter(logging.Filter):
    """为每条日志注入当前请求 ID（来自 contextvar），便于跨服务串联追踪。"""

    def filter(self, record: logging.LogRecord) -> bool:
        extra = dict(getattr(record, "extra_fields", {}) or {})
        extra.setdefault("request_id", _request_id_var.get())
        record.extra_fields = extra
        return True


def build_loki_streams(records, base_labels):
    """将 (timestamp_ns, message, extra_labels) 列表聚合成 Loki push streams。"""
    streams: dict = {}
    for ts, msg, extra in records:
        labels = dict(base_labels or {})
        if isinstance(extra, dict):
            labels.update(extra)
        labels.setdefault("level", "info")
        key = tuple(sorted(labels.items()))
        s = streams.get(key)
        if s is None:
            s = {"stream": dict(labels), "values": []}
            streams[key] = s
        s["values"].append([ts, msg])
    return list(streams.values())


class LokiHandler(logging.Handler):
    """把日志异步推送到 Loki（/loki/api/v1/push）。推送失败静默，绝不影响主流程。"""

    def __init__(self, url, labels=None, timeout=2.0, level=logging.NOTSET):
        super().__init__(level=level)
        self.url = url.rstrip("/") + "/loki/api/v1/push"
        self.labels = labels or {}
        self.timeout = timeout
        self._queue: queue.Queue = queue.Queue()
        self._stop = threading.Event()
        self._worker = threading.Thread(target=self._run, daemon=True, name="loki-handler")
        self._worker.start()

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            extra = getattr(record, "extra_fields", None) or {}
            labels = {"level": record.levelname.lower()}
            if isinstance(extra, dict):
                labels.update({k: str(v) for k, v in extra.items()})
            ts = str(int(record.created * 1_000_000_000))
            self._queue.put((ts, msg, labels))
        except Exception:  # pragma: no cover
            self.handleError(record)

    def _run(self):
        while not self._stop.is_set():
            try:
                item = self._queue.get(timeout=1)
            except queue.Empty:
                continue
            batch = [item]
            try:
                while len(batch) < 200:
                    batch.append(self._queue.get_nowait())
            except queue.Empty:
                pass
            self._push(batch)

    def _push(self, batch):
        streams = build_loki_streams(batch, self.labels)
        if not streams:
            return
        payload = {"streams": streams}
        try:
            requests.post(self.url, json=payload, timeout=self.timeout)
        except Exception:
            pass  # 静默失败，日志聚合不可用绝不能拖垮业务

    def close(self):
        self._stop.set()
        super().close()


def setup_logging():
    """配置 root 日志器：JSON 格式化 + stdout；LOKI_ENABLED 时追加 LokiHandler。"""
    root = logging.getLogger()
    root.setLevel(getattr(logging, str(settings.LOG_LEVEL).upper(), logging.INFO))

    # 幂等：先清空已有 handler，避免 reload / 多次调用造成重复输出
    for h in list(root.handlers):
        root.removeHandler(h)
        try:
            h.close()
        except Exception:
            pass

    formatter = JsonFormatter()
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    sh.addFilter(RequestIdFilter())
    root.addHandler(sh)

    if getattr(settings, "LOKI_ENABLED", False):
        lh = LokiHandler(
            url=settings.LOKI_URL,
            labels={"service": settings.LOKI_SERVICE_NAME, "env": settings.LOKI_ENV},
        )
        lh.setFormatter(formatter)
        root.addHandler(lh)

    # uvicorn 自身日志统一冒泡到 root，走同一套 JSON + Loki
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        lg = logging.getLogger(name)
        lg.handlers = []
        lg.propagate = True

    return root


def set_request_id(rid: str):
    _request_id_var.set(rid)


def get_request_id() -> str:
    return _request_id_var.get()


def clear_request_id():
    _request_id_var.set("-")
