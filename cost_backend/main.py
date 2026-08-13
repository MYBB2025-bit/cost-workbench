"""入口：装配路由、CORS、生命周期（建表+初始管理员）、Prometheus 监控、Loki 日志聚合、前端静态托管。"""
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

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


app = FastAPI(
    title=settings.APP_NAME,
    description="造价驻场工作台后端 API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)

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


# ---------- 中文 Swagger 文档（离线静态资源） ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
FRONTEND_DIST_DIR = os.path.normpath(os.path.join(BASE_DIR, "..", "cost_web", "dist"))


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    html = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{settings.APP_NAME} - API 文档",
        swagger_js_url="/static/swagger/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger/swagger-ui.css",
        swagger_favicon_url="/static/swagger/favicon-32x32.png",
    )
    # 离线汉化常见 UI 文案（DOM 文本替换）
    i18n_script = (
        "<script>"
        "(function(){"
        "var dict={"
        "'Authorize':'授权','Schemas':'模型','Responses':'响应','Parameters':'参数',"
        "'Request body':'请求体','Execute':'执行','Clear':'清空','Try it out':'试一试',"
        "'Cancel':'取消','Download':'下载','Overview':'概览','Authentication':'认证',"
        "'Value':'值','Description':'描述','Required':'必填','Example value':'示例值',"
        "'Model':'模型','Servers':'服务地址','No parameters':'无参数','Responses codes':'响应码'};"
        "function tr(){var w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT,null,false),n;"
        "while(n=w.nextNode()){var t=n.nodeValue.trim();if(dict[t])n.nodeValue=dict[t];}}"
        "var o=new MutationObserver(tr);o.observe(document.body,{childList:true,subtree:true});"
        "setTimeout(tr,300);setTimeout(tr,800);})();"
        "</script>"
    )
    new_body = html.body.replace(b"</body>", i18n_script.encode("utf-8") + b"</body>")
    return HTMLResponse(content=new_body)


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/", StaticFiles(directory=FRONTEND_DIST_DIR, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
