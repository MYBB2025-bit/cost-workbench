-- ==============================================
-- 造价驻场工作台｜基础表 RBAC + 客户端更新 + 造价核心
-- PostgreSQL 初始化脚本（生产环境执行；开发降级用 SQLite 由 init_db() 自动建表）
-- 注意：已调整建表顺序，确保外键引用表先创建
-- ==============================================

-- ============ 工程项目（核心业务隔离主体，须先于引用它的权限表）============
CREATE TABLE IF NOT EXISTS cost_project (
    id BIGSERIAL PRIMARY KEY,
    project_name VARCHAR(255) NOT NULL,
    project_code VARCHAR(64) UNIQUE,
    contract_amount DECIMAL(18,4),
    status VARCHAR(32),
    created_at TIMESTAMP DEFAULT now()
);

-- ============ RBAC ============
CREATE TABLE IF NOT EXISTS sys_user (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    real_name VARCHAR(64) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    org_id BIGINT,
    status SMALLINT DEFAULT 1,
    is_super BOOLEAN DEFAULT FALSE,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sys_role (
    id BIGSERIAL PRIMARY KEY,
    role_code VARCHAR(64) UNIQUE NOT NULL,
    role_name VARCHAR(64) NOT NULL,
    status SMALLINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sys_user_role (
    user_id BIGINT REFERENCES sys_user(id) ON DELETE CASCADE,
    role_id BIGINT REFERENCES sys_role(id) ON DELETE CASCADE,
    PRIMARY KEY(user_id, role_id)
);

CREATE TABLE IF NOT EXISTS sys_permission (
    id BIGSERIAL PRIMARY KEY,
    perm_code VARCHAR(128) UNIQUE NOT NULL,
    perm_name VARCHAR(128),
    parent_id BIGINT,
    resource VARCHAR(64),
    action VARCHAR(32)
);

CREATE TABLE IF NOT EXISTS sys_role_perm (
    role_id BIGINT REFERENCES sys_role(id) ON DELETE CASCADE,
    perm_id BIGINT REFERENCES sys_permission(id) ON DELETE CASCADE,
    PRIMARY KEY(role_id, perm_id)
);

-- ✅【造价核心】用户-项目数据权限（隔离造价员可见范围）
CREATE TABLE IF NOT EXISTS sys_user_project_perm (
    user_id BIGINT REFERENCES sys_user(id) ON DELETE CASCADE,
    project_id BIGINT REFERENCES cost_project(id) ON DELETE CASCADE,
    PRIMARY KEY(user_id, project_id)
);

CREATE TABLE IF NOT EXISTS sys_audit_log (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT,
    operate_type VARCHAR(64),
    resource_type VARCHAR(64),
    resource_id BIGINT,
    content JSONB,
    ip VARCHAR(64),
    created_at TIMESTAMP DEFAULT now()
);

-- ============ 客户端版本/补丁 ============
CREATE TABLE IF NOT EXISTS client_version (
    id BIGSERIAL PRIMARY KEY,
    version_code VARCHAR(32) UNIQUE NOT NULL,
    version_desc TEXT,
    force_update SMALLINT DEFAULT 0,
    min_compat_version VARCHAR(32),
    status SMALLINT DEFAULT 1,
    publish_time TIMESTAMP DEFAULT now(),
    full_pkg_minio_path VARCHAR(255),
    full_pkg_md5 VARCHAR(64),
    full_pkg_size BIGINT
);

CREATE TABLE IF NOT EXISTS client_patch (
    id BIGSERIAL PRIMARY KEY,
    from_version VARCHAR(32) NOT NULL,
    to_version VARCHAR(32) NOT NULL,
    patch_minio_path VARCHAR(255) NOT NULL,
    patch_md5 VARCHAR(64) NOT NULL,
    patch_size BIGINT NOT NULL,
    status SMALLINT DEFAULT 1
);

CREATE TABLE IF NOT EXISTS client_gray_release (
    id BIGSERIAL PRIMARY KEY,
    version_code VARCHAR(32),
    user_filter JSONB,
    enable SMALLINT DEFAULT 0
);

-- ============ 造价核心业务表 ============
-- 进度款审核（对应本地【09进度款审核】）
CREATE TABLE IF NOT EXISTS cost_progress_payment (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT REFERENCES cost_project(id),
    period_name VARCHAR(128),
    apply_amount DECIMAL(18,4),
    audit_amount DECIMAL(18,4),
    status VARCHAR(32),
    creator BIGINT REFERENCES sys_user(id),
    created_at TIMESTAMP DEFAULT now()
);

-- 进度款/估算 WBS 树节点（paymentStats 递归聚合基础）
CREATE TABLE IF NOT EXISTS cost_payment_node (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT REFERENCES cost_project(id),
    parent_id BIGINT REFERENCES cost_payment_node(id),
    name VARCHAR(255),
    estimate DECIMAL(18,4) DEFAULT 0,
    applied DECIMAL(18,4) DEFAULT 0,
    audited DECIMAL(18,4) DEFAULT 0,
    status VARCHAR(32),
    sort_order INTEGER DEFAULT 0
);

-- 核价库：总价 = 单价 × 工程量
CREATE TABLE IF NOT EXISTS cost_pricing (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT REFERENCES cost_project(id),
    name VARCHAR(255),
    spec VARCHAR(255),
    unit VARCHAR(32),
    category VARCHAR(64),
    supplier VARCHAR(128),
    price DECIMAL(18,4) DEFAULT 0,
    qty DECIMAL(18,4) DEFAULT 0,
    total DECIMAL(18,4) DEFAULT 0
);

-- 风险项
CREATE TABLE IF NOT EXISTS cost_risk_item (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT REFERENCES cost_project(id),
    risk_type VARCHAR(64),
    level VARCHAR(32),
    title VARCHAR(255),
    desc TEXT,
    due VARCHAR(32),
    status VARCHAR(32),
    related_type VARCHAR(64),
    related_id BIGINT
);

-- 预警规则
CREATE TABLE IF NOT EXISTS cost_warning_rule (
    id BIGSERIAL PRIMARY KEY,
    rule_type VARCHAR(64),
    threshold_days INTEGER DEFAULT 7,
    enabled SMALLINT DEFAULT 1
);

-- 最终资料台账
CREATE TABLE IF NOT EXISTS cost_ledger_doc (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT REFERENCES cost_project(id),
    category VARCHAR(64),
    name VARCHAR(255),
    owner VARCHAR(64),
    due VARCHAR(32),
    status VARCHAR(32),
    finished_at VARCHAR(32)
);

-- 附件
CREATE TABLE IF NOT EXISTS cost_attachment (
    id BIGSERIAL PRIMARY KEY,
    owner_type VARCHAR(64),
    owner_id BIGINT,
    filename VARCHAR(255),
    storage_key VARCHAR(255),
    size BIGINT,
    md5 VARCHAR(64),
    uploaded_by BIGINT,
    created_at TIMESTAMP DEFAULT now()
);

-- ============ 造价业务扩展：预算 / 变更 / 签证 / 结算 ============
CREATE TABLE IF NOT EXISTS cost_budget_item (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT REFERENCES cost_project(id),
    parent_id BIGINT REFERENCES cost_budget_item(id),
    item_no VARCHAR(64),
    name VARCHAR(255) NOT NULL,
    spec VARCHAR(255),
    unit VARCHAR(32),
    qty DECIMAL(18,4) DEFAULT 0,
    unit_price DECIMAL(18,4) DEFAULT 0,
    total_price DECIMAL(18,4) DEFAULT 0,
    category VARCHAR(64),
    work_type VARCHAR(64),
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cost_budget_import_log (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT REFERENCES cost_project(id),
    filename VARCHAR(255),
    total_rows INTEGER DEFAULT 0,
    success_rows INTEGER DEFAULT 0,
    error_rows INTEGER DEFAULT 0,
    errors JSONB,
    status VARCHAR(32) DEFAULT 'pending',
    uploaded_by BIGINT,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cost_change_order (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT REFERENCES cost_project(id),
    change_no VARCHAR(64),
    change_name VARCHAR(255),
    change_type VARCHAR(64),
    amount DECIMAL(18,4) DEFAULT 0,
    status VARCHAR(32) DEFAULT 'draft',
    creator BIGINT REFERENCES sys_user(id),
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cost_change_item (
    id BIGSERIAL PRIMARY KEY,
    change_order_id BIGINT REFERENCES cost_change_order(id),
    budget_item_id BIGINT REFERENCES cost_budget_item(id),
    name VARCHAR(255),
    unit VARCHAR(32),
    before_qty DECIMAL(18,4) DEFAULT 0,
    after_qty DECIMAL(18,4) DEFAULT 0,
    delta_qty DECIMAL(18,4) DEFAULT 0,
    unit_price DECIMAL(18,4) DEFAULT 0,
    amount DECIMAL(18,4) DEFAULT 0,
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cost_visa (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT REFERENCES cost_project(id),
    visa_no VARCHAR(64),
    visa_date VARCHAR(32),
    content TEXT,
    amount DECIMAL(18,4) DEFAULT 0,
    status VARCHAR(32) DEFAULT 'draft',
    creator BIGINT REFERENCES sys_user(id),
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cost_settlement (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT REFERENCES cost_project(id),
    settlement_no VARCHAR(64),
    settlement_name VARCHAR(255),
    settlement_type VARCHAR(32) DEFAULT 'midterm',
    total_amount DECIMAL(18,4) DEFAULT 0,
    status VARCHAR(32) DEFAULT 'draft',
    creator BIGINT REFERENCES sys_user(id),
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cost_settlement_item (
    id BIGSERIAL PRIMARY KEY,
    settlement_id BIGINT REFERENCES cost_settlement(id),
    budget_item_id BIGINT REFERENCES cost_budget_item(id),
    name VARCHAR(255),
    unit VARCHAR(32),
    settle_qty DECIMAL(18,4) DEFAULT 0,
    unit_price DECIMAL(18,4) DEFAULT 0,
    amount DECIMAL(18,4) DEFAULT 0,
    sort_order INTEGER DEFAULT 0
);

-- ============ 初始化基础角色 ============
INSERT INTO sys_role(role_code, role_name) VALUES
('cost_admin','造价系统管理员'),
('cost_editor','造价驻场员'),
('cost_leader','部门负责人'),
('readonly_viewer','只读审计')
ON CONFLICT (role_code) DO NOTHING;

-- 初始权限（示例，按需补充）
INSERT INTO sys_permission(perm_code, perm_name, resource, action) VALUES
('project:view','查看项目','project','view'),
('project:create','创建项目','project','create'),
('project:update','编辑项目','project','update'),
('project:delete','删除项目','project','delete'),
('progress:view','查看进度款','progress','view'),
('progress:create','创建进度款','progress','create'),
('progress:update','编辑进度款','progress','update'),
('pricing:view','查看核价库','pricing','view'),
('pricing:create','创建核价','pricing','create'),
('pricing:update','编辑核价','pricing','update'),
('risk:view','查看风险预警','risk','view'),
('ledger:view','查看台账','ledger','view'),
('client:version:view','查看客户端版本','client','view'),
('client:version:publish','发布版本','client','publish'),
('client:patch:upload','上传补丁','client','upload'),
('budget:view','查看预算清单','budget','view'),
('budget:create','创建预算清单','budget','create'),
('budget:update','编辑预算清单','budget','update'),
('budget:delete','删除预算清单','budget','delete'),
('budget:import','导入预算清单','budget','import'),
('change:view','查看变更签证','change','view'),
('change:create','创建变更签证','change','create'),
('change:update','编辑变更签证','change','update'),
('change:delete','删除变更签证','change','delete'),
('settlement:view','查看结算','settlement','view'),
('settlement:create','创建结算','settlement','create'),
('settlement:update','编辑结算','settlement','update'),
('settlement:delete','删除结算','settlement','delete')
ON CONFLICT (perm_code) DO NOTHING;

-- 关联：造价管理员拥有全部权限
INSERT INTO sys_role_perm(role_id, perm_id)
SELECT r.id, p.id FROM sys_role r, sys_permission p
WHERE r.role_code = 'cost_admin'
ON CONFLICT DO NOTHING;

-- ============ 异步任务作业 ============
CREATE TABLE IF NOT EXISTS task_job (
    id BIGSERIAL PRIMARY KEY,
    job_uuid VARCHAR(64) NOT NULL UNIQUE,
    task_type VARCHAR(64) NOT NULL,
    status VARCHAR(32),
    progress INTEGER DEFAULT 0,
    total INTEGER DEFAULT 0,
    processed INTEGER DEFAULT 0,
    result JSON,
    error TEXT,
    created_by BIGINT,
    created_at TIMESTAMP DEFAULT now(),
    started_at TIMESTAMP,
    finished_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_task_job_task_type ON task_job (task_type);

