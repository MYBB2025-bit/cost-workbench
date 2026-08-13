"""Loki 日志聚合测试：JSON 格式化、stream 聚合、Loki push、请求 ID 注入、setup 开关。"""
import json
import logging

from core.config import settings
from core.logging_config import (
    JsonFormatter,
    LokiHandler,
    RequestIdFilter,
    build_loki_streams,
    set_request_id,
    setup_logging,
)


def test_json_formatter():
    fmt = JsonFormatter()
    logger = logging.getLogger("test.json.fmt")
    logger.handlers = []
    rec = logger.makeRecord("test.json.fmt", logging.INFO, "path", 10, "hello world", None, None)
    data = json.loads(fmt.format(rec))
    assert data["level"] == "INFO"
    assert data["message"] == "hello world"
    assert data["logger"] == "test.json.fmt"
    assert "time" in data


def test_json_formatter_merges_extra():
    fmt = JsonFormatter()
    logger = logging.getLogger("test.json.extra")
    logger.handlers = []
    rec = logger.makeRecord("test.json.extra", logging.WARNING, "p", 1, "x", None, None)
    rec.extra_fields = {"request_id": "r-1", "path": "/a"}
    data = json.loads(fmt.format(rec))
    assert data["request_id"] == "r-1"
    assert data["path"] == "/a"
    assert data["level"] == "WARNING"


def test_build_loki_streams():
    recs = [
        ("100", "msg1", {"level": "info", "a": "1"}),
        ("101", "msg2", {"level": "info", "a": "1"}),
        ("102", "msg3", {"level": "error", "a": "1"}),
    ]
    streams = build_loki_streams(recs, {"service": "svc"})
    assert len(streams) == 2
    by_level = {s["stream"]["level"]: s for s in streams}
    assert len(by_level["info"]["values"]) == 2
    assert len(by_level["error"]["values"]) == 1
    assert streams[0]["stream"]["service"] == "svc"


def test_loki_handler_push(monkeypatch):
    import core.logging_config as m

    sent = {}

    def fake_post(url, json=None, timeout=None):
        sent["url"] = url
        sent["json"] = json

        class R:
            status_code = 204

        return R()

    monkeypatch.setattr(m.requests, "post", fake_post)
    h = LokiHandler(url="http://loki:3100", labels={"service": "svc"})
    try:
        h._push([("100", "m1", {"level": "info"}), ("101", "m2", {"level": "info"})])
    finally:
        h.close()
    assert sent["url"] == "http://loki:3100/loki/api/v1/push"
    streams = sent["json"]["streams"]
    assert len(streams) == 1
    assert streams[0]["stream"]["service"] == "svc"
    assert len(streams[0]["values"]) == 2


def test_loki_handler_silent_on_error(monkeypatch):
    import core.logging_config as m

    def boom(*a, **k):
        raise RuntimeError("loki down")

    monkeypatch.setattr(m.requests, "post", boom)
    h = LokiHandler(url="http://loki:3100")
    try:
        # 推送失败必须静默，不能抛异常
        h._push([("100", "m1", {"level": "info"})])
    finally:
        h.close()


def test_request_id_filter():
    set_request_id("abc-123")
    f = RequestIdFilter()
    rec = logging.LogRecord("x", logging.INFO, "p", 1, "m", None, None)
    assert f.filter(rec) is True
    assert rec.extra_fields["request_id"] == "abc-123"


def test_setup_logging_respects_enabled_flag(monkeypatch):
    monkeypatch.setattr(settings, "LOKI_ENABLED", False)
    root = setup_logging()
    assert not any(isinstance(h, LokiHandler) for h in root.handlers)

    monkeypatch.setattr(settings, "LOKI_ENABLED", True)
    monkeypatch.setattr(settings, "LOKI_URL", "http://loki:3100")
    monkeypatch.setattr(settings, "LOKI_SERVICE_NAME", "svc")
    monkeypatch.setattr(settings, "LOKI_ENV", "test")
    root = setup_logging()
    lh = [h for h in root.handlers if isinstance(h, LokiHandler)]
    assert len(lh) == 1
    lh[0].close()

    # 还原，避免影响其它测试
    monkeypatch.setattr(settings, "LOKI_ENABLED", False)
