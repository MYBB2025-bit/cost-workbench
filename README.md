# 造价驻场工作台（重构版）

面向造价驻场业务的 **前后端分离** 工作台。采用 **模块化单体（FastAPI）+ Vue3 SPA** 架构，配套 PostgreSQL / Redis / MinIO，支持客户端 exe 的差分补丁（bsdiff）自更新与灰度发布。

## 架构总览

```
浏览器(Vue3 SPA)
   │  /api/*  (Nginx 分流)
   ▼
FastAPI 模块化单体  ──┬── PostgreSQL  业务数据
   │                 ├── Redis       缓存/会话/限流(预留)
   │                 └── MinIO       补丁/附件大文件(不占 FastAPI 算力)
   ▼
exe 客户端(bsdiff 自更新)  ←── 版本检测 / 差分补丁下载 / 灰度
```

- **后端**：`cost_backend/` —— FastAPI，按领域分层 `core / db / api/v1 / service / repository / utils`
- **前端**：`cost_web/` —— Vue3 + Vite + TS + Pinia + VueRouter4 + Element Plus
- **基础设施**：`docker-compose.yml` / `nginx/` / `prometheus/`

## 目录结构

```
cost_backend/
├─ .env / .env.example       环境变量（DB/Redis/MinIO/安全）
├─ main.py                   入口（路由挂载、CORS、lifespan、Prometheus）
├─ core/                     config / security(JWT+哈希) / deps(RBAC+数据权限)
├─ db/                       base / session / models(ORM) / migrations/001_init.sql
├─ api/v1/                   auth / client_upgrade(重点) / project / progress / pricing / risk / ledger
├─ service/                  业务层（含 paymentStats / 核价 / 风险预警 移植逻辑）
├─ repository/               数据层
├─ utils/                    storage(MinIO本地降级) / md5 / audit / version
├─ tools/client_updater.py   客户端 exe 自更新器(bsdiff)
└─ tests/                    pytest（领域单测 + API 冒烟，10 项全绿）

cost_web/
├─ src/api/                  axios 封装 + 各模块请求
├─ src/store/                user(令牌/角色) + permission(后端驱动动态路由)
├─ src/directive/            v-permission 按钮级权限指令
├─ src/router/               路由（登录 + Layout + 动态追加）
├─ src/views/                login / dashboard / project / progress / pricing / risk / ledger / client
└─ nginx.conf                Nginx 托管 + /api 代理 + 补丁限流
```

## 快速开始

### 方式一：全栈（Docker Compose，生产推荐）
```bash
docker compose up -d --build
# 前端 http://localhost     后端 http://localhost:8000/docs
```
默认管理员：`admin / admin123`

### 方式二：本地开发（无需外部依赖，SQLite + 本地文件降级）
```bash
cd cost_backend
cp .env.example .env          # 已默认 SQLite + USE_LOCAL_STORAGE=true
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# 另开终端
cd ../cost_web
npm install
npm run dev                   # http://localhost:3000
```
> 通过 `.env` 切换：把 `DATABASE_URL` 改为 `postgresql://...`、`USE_LOCAL_STORAGE=false` 即接入全栈。

## 核心能力

- **RBAC + 数据权限**：`sys_user / sys_role / sys_permission / sys_user_role / sys_role_perm`；造价特有的 `sys_user_project_perm` 按项目隔离数据，后端 `get_user_project_ids` 依赖自动注入。
- **客户端更新（重点）**：
  - `GET /api/v1/client/version/check` 版本检测 + 灰度白名单判断 + 推荐 bsdiff 补丁
  - `GET /api/v1/client/patch/download/{id}` 流式下载（不占内存，Nginx 限流 2M）
  - `POST /api/v1/client/version/publish`、`POST /api/v1/client/patch/upload` 后台发布
  - 客户端 `tools/client_updater.py` 实现断点续传 + MD5 校验 + 打补丁失败自动回滚
- **造价核心逻辑（已移植并修复）**：
  - 进度款 WBS 递归统计 `paymentStats`（修复父/子互斥累加 bug）
  - 核价库总价 = 单价 × 工程量
  - 风险 / 预警 / 最终资料台账采集（修复数组缺失即崩溃的健壮性 bug）

## 已修复的历史缺陷

| # | 缺陷 | 位置 | 修复 |
|---|------|------|------|
| 1 | 风险/预警采集数组无兜底，缺字段即崩溃 | `collectRiskItems/collectWarningItems` | 改为 DB 查询，天然安全（空集=[]） |
| 2 | 进度款父节点自带值会吞掉子节点汇总 | `paymentStats: totalEstimate=ownEst \|\| childEst` | `total = 本级 + Σ(子汇总)`，父/子相加 |
| 3 | CSV 导入遇引号内逗号错位 | `line.split(',')` | 解析函数 + 后端结构化存储 |

## 测试

```bash
cd cost_backend
pytest tests -v            # 10 passed（领域逻辑 + API 全链路，含补丁下载内容一致性）
```

## 监控

- `prometheus/prometheus.yml` + `alert.yml`：API 5xx 错误率、补丁下载 P95 延迟告警
- 后端已通过 `prometheus-fastapi-instrumentator` 暴露 `/metrics`（依赖可选，未安装不影响主流程）
