"""全部 ORM 模型（与 db/migrations/001_init.sql 对齐）。
使用跨数据库类型（BigInteger/JSON/DECIMAL），便于 SQLite 降级开发与 PostgreSQL 生产共用一套代码。
"""
from datetime import datetime

from sqlalchemy import (
    DECIMAL,
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from core.config import settings
from db.base import Base

# SQLite 仅对 INTEGER PRIMARY KEY 自增；PostgreSQL 用 BIGINT/BIGSERIAL。
# 双模式下按数据库类型选择主键类型，保证本地开发与生产一致可用。
PKType = Integer if settings.IS_SQLITE else BigInteger


# ============ RBAC ============
class SysUser(Base):
    __tablename__ = "sys_user"
    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    real_name: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    org_id: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)  # 0禁用 1正常
    is_super: Mapped[bool] = mapped_column(Boolean, default=False)  # 超级管理员
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class SysRole(Base):
    __tablename__ = "sys_role"
    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    role_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    role_name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SysUserRole(Base):
    __tablename__ = "sys_user_role"
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sys_user.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sys_role.id", ondelete="CASCADE"), primary_key=True)


class SysPermission(Base):
    __tablename__ = "sys_permission"
    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    perm_code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    perm_name: Mapped[str | None] = mapped_column(String(128))
    parent_id: Mapped[int | None] = mapped_column(BigInteger)
    resource: Mapped[str | None] = mapped_column(String(64))
    action: Mapped[str | None] = mapped_column(String(32))


class SysRolePerm(Base):
    __tablename__ = "sys_role_perm"
    role_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sys_role.id", ondelete="CASCADE"), primary_key=True)
    perm_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sys_permission.id", ondelete="CASCADE"), primary_key=True)


class SysUserProjectPerm(Base):
    """【造价核心】用户-项目数据权限（隔离造价员可见范围）。"""
    __tablename__ = "sys_user_project_perm"
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sys_user.id", ondelete="CASCADE"), primary_key=True)
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cost_project.id", ondelete="CASCADE"), primary_key=True)


class SysAuditLog(Base):
    __tablename__ = "sys_audit_log"
    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger)
    operate_type: Mapped[str | None] = mapped_column(String(64))
    resource_type: Mapped[str | None] = mapped_column(String(64))
    resource_id: Mapped[int | None] = mapped_column(BigInteger)
    content: Mapped[dict | None] = mapped_column(JSON)
    ip: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ============ 客户端更新 ============
class ClientVersion(Base):
    __tablename__ = "client_version"
    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    version_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    version_desc: Mapped[str | None] = mapped_column(Text)
    force_update: Mapped[int] = mapped_column(SmallInteger, default=0)
    min_compat_version: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    publish_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # 整包（无差分补丁时的兜底更新包）存储信息
    full_pkg_minio_path: Mapped[str | None] = mapped_column(String(255))
    full_pkg_md5: Mapped[str | None] = mapped_column(String(64))
    full_pkg_size: Mapped[int | None] = mapped_column(BigInteger)


class ClientPatch(Base):
    __tablename__ = "client_patch"
    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    from_version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    to_version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    patch_minio_path: Mapped[str] = mapped_column(String(255), nullable=False)
    patch_md5: Mapped[str] = mapped_column(String(64), nullable=False)
    patch_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)


class ClientGrayRelease(Base):
    __tablename__ = "client_gray_release"
    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    version_code: Mapped[str | None] = mapped_column(String(32))
    user_filter: Mapped[dict | None] = mapped_column(JSON)
    enable: Mapped[int] = mapped_column(SmallInteger, default=0)


# ============ 造价核心业务 ============
class CostProject(Base):
    """工程项目（核心业务隔离主体）。"""
    __tablename__ = "cost_project"
    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    project_code: Mapped[str | None] = mapped_column(String(64), unique=True)
    contract_amount: Mapped[float | None] = mapped_column(DECIMAL(18, 4))
    status: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CostProgressPayment(Base):
    """进度款审核记录（对应本地【09进度款审核】）。"""
    __tablename__ = "cost_progress_payment"
    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    project_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("cost_project.id"))
    period_name: Mapped[str | None] = mapped_column(String(128))
    apply_amount: Mapped[float | None] = mapped_column(DECIMAL(18, 4))
    audit_amount: Mapped[float | None] = mapped_column(DECIMAL(18, 4))
    status: Mapped[str | None] = mapped_column(String(32))
    creator: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("sys_user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CostPaymentNode(Base):
    """进度款/估算 WBS 树节点（paymentStats 递归聚合的数据基础）。"""
    __tablename__ = "cost_payment_node"
    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    project_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("cost_project.id"))
    parent_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("cost_payment_node.id"))
    name: Mapped[str | None] = mapped_column(String(255))
    estimate: Mapped[float] = mapped_column(DECIMAL(18, 4), default=0)     # 本级估算/申报值
    applied: Mapped[float] = mapped_column(DECIMAL(18, 4), default=0)      # 已申报
    audited: Mapped[float] = mapped_column(DECIMAL(18, 4), default=0)      # 已审核
    status: Mapped[str | None] = mapped_column(String(32))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class CostPricing(Base):
    """核价库：总价 = 单价 × 工程量。"""
    __tablename__ = "cost_pricing"
    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    project_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("cost_project.id"))
    name: Mapped[str | None] = mapped_column(String(255))
    spec: Mapped[str | None] = mapped_column(String(255))
    unit: Mapped[str | None] = mapped_column(String(32))
    category: Mapped[str | None] = mapped_column(String(64))
    supplier: Mapped[str | None] = mapped_column(String(128))
    price: Mapped[float] = mapped_column(DECIMAL(18, 4), default=0)  # 单价
    qty: Mapped[float] = mapped_column(DECIMAL(18, 4), default=0)    # 工程量
    total: Mapped[float] = mapped_column(DECIMAL(18, 4), default=0)  # 总价（price*qty）


class CostRiskItem(Base):
    """风险项（采集自各业务对象）。"""
    __tablename__ = "cost_risk_item"
    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    project_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("cost_project.id"))
    risk_type: Mapped[str | None] = mapped_column(String(64))   # overdue/over_budget/...
    level: Mapped[str | None] = mapped_column(String(32))       # high/mid/low
    title: Mapped[str | None] = mapped_column(String(255))
    desc: Mapped[str | None] = mapped_column(Text)
    due: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str | None] = mapped_column(String(32))
    related_type: Mapped[str | None] = mapped_column(String(64))
    related_id: Mapped[int | None] = mapped_column(BigInteger)


class CostWarningRule(Base):
    """预警规则配置。"""
    __tablename__ = "cost_warning_rule"
    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    rule_type: Mapped[str | None] = mapped_column(String(64))   # due_soon/over_budget/...
    threshold_days: Mapped[int] = mapped_column(Integer, default=7)
    enabled: Mapped[int] = mapped_column(SmallInteger, default=1)


class CostLedgerDoc(Base):
    """最终资料台账文档。"""
    __tablename__ = "cost_ledger_doc"
    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    project_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("cost_project.id"))
    category: Mapped[str | None] = mapped_column(String(64))
    name: Mapped[str | None] = mapped_column(String(255))
    owner: Mapped[str | None] = mapped_column(String(64))
    due: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str | None] = mapped_column(String(32))   # pending/done
    finished_at: Mapped[str | None] = mapped_column(String(32))


class CostAttachment(Base):
    """附件（大文件走 MinIO/本地，不进 DB 主体）。"""
    __tablename__ = "cost_attachment"
    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    owner_type: Mapped[str | None] = mapped_column(String(64))
    owner_id: Mapped[int | None] = mapped_column(BigInteger)
    filename: Mapped[str | None] = mapped_column(String(255))
    storage_key: Mapped[str | None] = mapped_column(String(255))
    size: Mapped[int | None] = mapped_column(BigInteger)
    md5: Mapped[str | None] = mapped_column(String(64))
    uploaded_by: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ============ 造价业务扩展：预算 / 变更 / 签证 / 结算 ============
class CostBudgetItem(Base):
    """预算清单项（工程量清单 BOQ）。支持树形结构：分部分项 → 清单项。"""
    __tablename__ = "cost_budget_item"
    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    project_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("cost_project.id"))
    parent_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("cost_budget_item.id"))
    item_no: Mapped[str | None] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    spec: Mapped[str | None] = mapped_column(String(255))
    unit: Mapped[str | None] = mapped_column(String(32))
    qty: Mapped[float] = mapped_column(DECIMAL(18, 4), default=0)
    unit_price: Mapped[float] = mapped_column(DECIMAL(18, 4), default=0)
    total_price: Mapped[float] = mapped_column(DECIMAL(18, 4), default=0)
    category: Mapped[str | None] = mapped_column(String(64))
    work_type: Mapped[str | None] = mapped_column(String(64))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CostBudgetImportLog(Base):
    """预算清单 Excel 导入日志。"""
    __tablename__ = "cost_budget_import_log"
    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    project_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("cost_project.id"))
    filename: Mapped[str | None] = mapped_column(String(255))
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    success_rows: Mapped[int] = mapped_column(Integer, default=0)
    error_rows: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str | None] = mapped_column(String(32), default="pending")
    uploaded_by: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CostChangeOrder(Base):
    """变更单（设计变更 / 现场变更 / 业主要求）。"""
    __tablename__ = "cost_change_order"
    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    project_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("cost_project.id"))
    change_no: Mapped[str | None] = mapped_column(String(64), index=True)
    change_name: Mapped[str | None] = mapped_column(String(255))
    change_type: Mapped[str | None] = mapped_column(String(64))
    amount: Mapped[float] = mapped_column(DECIMAL(18, 4), default=0)
    status: Mapped[str | None] = mapped_column(String(32), default="draft")
    creator: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("sys_user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CostChangeItem(Base):
    """变更明细：一项变更可包含多个清单项调整。"""
    __tablename__ = "cost_change_item"
    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    change_order_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("cost_change_order.id"))
    budget_item_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("cost_budget_item.id"))
    name: Mapped[str | None] = mapped_column(String(255))
    unit: Mapped[str | None] = mapped_column(String(32))
    before_qty: Mapped[float] = mapped_column(DECIMAL(18, 4), default=0)
    after_qty: Mapped[float] = mapped_column(DECIMAL(18, 4), default=0)
    delta_qty: Mapped[float] = mapped_column(DECIMAL(18, 4), default=0)
    unit_price: Mapped[float] = mapped_column(DECIMAL(18, 4), default=0)
    amount: Mapped[float] = mapped_column(DECIMAL(18, 4), default=0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class CostVisa(Base):
    """签证单（现场签证 / 零星工程）。"""
    __tablename__ = "cost_visa"
    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    project_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("cost_project.id"))
    visa_no: Mapped[str | None] = mapped_column(String(64), index=True)
    visa_date: Mapped[str | None] = mapped_column(String(32))
    content: Mapped[str | None] = mapped_column(Text)
    amount: Mapped[float] = mapped_column(DECIMAL(18, 4), default=0)
    status: Mapped[str | None] = mapped_column(String(32), default="draft")
    creator: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("sys_user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CostSettlement(Base):
    """结算单（期中 / 最终结算）。"""
    __tablename__ = "cost_settlement"
    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    project_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("cost_project.id"))
    settlement_no: Mapped[str | None] = mapped_column(String(64), index=True)
    settlement_name: Mapped[str | None] = mapped_column(String(255))
    settlement_type: Mapped[str | None] = mapped_column(String(32), default="midterm")
    total_amount: Mapped[float] = mapped_column(DECIMAL(18, 4), default=0)
    status: Mapped[str | None] = mapped_column(String(32), default="draft")
    creator: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("sys_user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CostSettlementItem(Base):
    """结算明细：按预算清单项汇总结算工程量与金额。"""
    __tablename__ = "cost_settlement_item"
    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    settlement_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("cost_settlement.id"))
    budget_item_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("cost_budget_item.id"))
    name: Mapped[str | None] = mapped_column(String(255))
    unit: Mapped[str | None] = mapped_column(String(32))
    settle_qty: Mapped[float] = mapped_column(DECIMAL(18, 4), default=0)
    unit_price: Mapped[float] = mapped_column(DECIMAL(18, 4), default=0)
    amount: Mapped[float] = mapped_column(DECIMAL(18, 4), default=0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


# ============ 异步任务作业（Celery job 状态追踪）============
class TaskJob(Base):
    """后台异步任务作业记录，用于前端轮询进度 / 下载结果。"""
    __tablename__ = "task_job"
    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    job_uuid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # budget_import / ledger_export
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending/running/success/failed
    progress: Mapped[int] = mapped_column(Integer, default=0)     # 0-100
    total: Mapped[int] = mapped_column(Integer, default=0)
    processed: Mapped[int] = mapped_column(Integer, default=0)
    result: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
