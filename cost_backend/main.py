"""入口：装配路由、CORS、生命周期（建表+初始管理员）、Prometheus 监控、Loki 日志聚合。"""
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from db.session import SessionLocal, init_db
from service import auth_service

try:
    from prometheus_fastapi_instrumentator import Instrumentator

    _HAS_PROM = True
except Exception:  # 未安装监控依赖时不影响主流程
    _HAS_PROM = False

from api.v1 import (
    auth,
    budget,
    change,
    client_upgrade,
    ledger,
    migration,
    pricing,
    progress,
    project,
    risk,
    settlement,
    stats,
    system,
    task,
)
from core.logging_config import request_id_var, setup_logging

setup_logging()
logger = logging.getLogger("cost.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with SessionLocal() as db:
        await init_db()
        await auth_service.init_admin(db)
    yield


app = FastAPI(title=settings.APP_NAME, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_log_middleware(request: Request, call_next):
    """为每个请求生成/透传 X-Request-ID，并记录结构化访问日志（含耗时）。"""
    rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    request_id_var.set(rid)
    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = rid
        return response
    finally:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "http request",
            extra={
                "extra_fields": {
                    "request_id": rid,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status,
                    "duration_ms": duration_ms,
                }
            },
        )
        request_id_var.set("-")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": f"服务器内部错误: {exc}"})


# 路由挂载
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(client_upgrade.router, prefix=settings.API_PREFIX)
app.include_router(project.router, prefix=settings.API_PREFIX)
app.include_router(progress.router, prefix=settings.API_PREFIX)
app.include_router(pricing.router, prefix=settings.API_PREFIX)
app.include_router(budget.router, prefix=settings.API_PREFIX)
app.include_router(change.router, prefix=settings.API_PREFIX)
app.include_router(settlement.router, prefix=settings.API_PREFIX)
app.include_router(risk.router, prefix=settings.API_PREFIX)
app.include_router(system.router, prefix=settings.API_PREFIX)
app.include_router(ledger.router, prefix=settings.API_PREFIX)
app.include_router(stats.router, prefix=settings.API_PREFIX)
app.include_router(task.router, prefix=settings.API_PREFIX)
app.include_router(migration.router, prefix=settings.API_PREFIX)


@app.get("/health", tags=["系统"])
async def health():
    return {"status": "ok", "service": settings.APP_NAME}


if _HAS_PROM:
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
