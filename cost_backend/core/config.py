"""应用配置：环境变量驱动。
支持两种运行模式：
- 全栈模式（目标生产）：PostgreSQL + Redis + MinIO
- 本地降级模式（开发/沙箱无外部依赖）：SQLite + 内存缓存 + 本地文件系统
通过 DATABASE_URL / REDIS_URL / MINIO_* 与 USE_LOCAL_STORAGE 切换。
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # ---- 服务 ----
    API_PREFIX: str = "/api/v1"
    APP_NAME: str = "造价驻场工作台API"
    DEBUG: bool = False

    # ---- 安全 ----
    SECRET_KEY: str = "dev-secret-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 240

    # ---- 数据库（异步）----
    # 全栈：postgresql://postgres:123456@localhost:5432/cost_workbench
    # 降级：sqlite+aiosqlite:///./cost.db
    DATABASE_URL: str = "postgresql://postgres:123456@localhost:5432/cost_workbench"

    # ---- Redis ----
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    CACHE_TTL_SECONDS: int = 300

    # ---- Celery 异步任务（broker/backend 默认复用 Redis）----
    CELERY_BROKER_URL: str | None = None   # 为空时回落到 REDIS_URL
    CELERY_RESULT_BACKEND: str | None = None
    CELERY_TASK_ALWAYS_EAGER: bool = False     # 测试/无 broker 时置 true，任务本地同步执行
    CELERY_TASK_EAGER_PROPAGATES: bool = False

    # ---- 日志 / Loki 聚合 ----
    LOG_LEVEL: str = "INFO"
    LOKI_ENABLED: bool = False            # 置 true 由应用直接推送结构化日志到 Loki
    LOKI_URL: str = "http://localhost:3100"
    LOKI_SERVICE_NAME: str = "cost-backend"
    LOKI_ENV: str = "dev"

    # ---- MinIO ----
    MINIO_ENDPOINT: str = "127.0.0.1:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_PATCH: str = "cost-patch"
    MINIO_BUCKET_ATTACH: str = "cost-attach"
    MINIO_SECURE: bool = False

    # ---- 本地降级存储 ----
    USE_LOCAL_STORAGE: bool = False
    LOCAL_PATCH_DIR: str = "./patches"      # 差分补丁存放
    LOCAL_UPLOAD_DIR: str = "./uploads"     # 附件存放

    # ---- 历史数据迁移（183MB 真实业务数据）----
    # 待迁移的源 JSON 路径（相对 backend 工作目录）。仅超级管理员可触发迁移。
    MIGRATION_DATA_PATH: str = "../data/user-data.json"

    # ---- 初始管理员 ----
    INIT_ADMIN_USERNAME: str = "admin"
    INIT_ADMIN_PASSWORD: str = "admin123"
    INIT_ADMIN_REAL_NAME: str = "系统管理员"

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        url = self.DATABASE_URL.strip()
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url  # sqlite+aiosqlite:///... 或 其他

    @property
    def IS_SQLITE(self) -> bool:
        return self.ASYNC_DATABASE_URL.startswith("sqlite")


settings = Settings()
