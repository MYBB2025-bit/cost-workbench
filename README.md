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
└─ tests/                    pytest（领域单测 + API 冒烟 + 异步/日志/迁移，46 项全绿）

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
- **Loki 日志聚合**：后端/worker 用应用内 `LokiHandler` 直接 push 结构化 JSON 日志；前端由 Promtail 抓取容器 stdout；Grafana（:3000）预置 Loki 数据源可视化。

## 测试

```bash
cd cost_backend
pytest tests -v            # 46 passed（领域逻辑 + API 全链路 + Celery 异步 + Loki + 183MB 数据迁移冒烟）
# 前端
cd ../cost_web && npm run build   # vue-tsc 零错误
# 一键本地 CI（复刻 GitHub Actions）
make ci
```

## 发布流程闭环

把 **版本打标 → CI 构建 → 发布说明 → 一键部署/回滚** 串成一个闭环。

### 1. 版本与镜像打标
- 根目录 `VERSION` 文件是唯一版本源（语义化版本，如 `1.0.0`）。
- `docker-compose.yml` 的四个服务镜像统一为 `cost-{backend,worker,flower,web}:${IMAGE_TAG:-latest}`；可选 `DOCKER_REGISTRY` 前缀支持推送私有/公共仓库（如 `ghcr.io/<org>/`）。
- 本地开发：`docker compose up -d --build`（用 build 上下文现编，标签 latest）。
- 版本化部署：`IMAGE_TAG=1.0.0 docker compose up -d`。

### 2. CI（`.github/workflows/ci.yml`）
- `backend`：Python 3.11/3.12 矩阵，ruff + pytest（SQLite 降级 + Celery eager）。
- `frontend`：Node 20，`npm ci` + `npm run build`。
- `docker`（仅 main 推送）：镜像打标 `:<version>` / `:latest` / `:sha-<sha>`。
- `release`（仅 `v*` 标签推送）：构建全部镜像 → `scripts/gen-release-notes.sh` 生成发布说明 → `docker save` 打包镜像 tarball → 通过 `softprops/action-gh-release` 创建 GitHub Release（含说明 + 镜像 tarball）。

### 3. 发布说明生成
```bash
bash scripts/gen-release-notes.sh 1.1.0 > RELEASES.md
```
基于 git 历史（上一 tag → 当前版本），按模块（Celery / Loki / 前端增强 / CI / 数据迁移 / 发布闭环）归纳变更并列出提交明细。非 git 环境下退化为仅输出版本与日期。

### 4. 一键脚本
```bash
make release v=1.1.0     # 升版 + 构建版本化镜像 + 生成说明 + 更新 CHANGELOG + 写 .env(IMAGE_TAG)
make deploy  v=1.1.0     # 按版本拉起（docker compose up -d），并记入 releases/history.log
make rollback            # 回退到 history 中上一部署版本并重部署
```
等价脚本：`scripts/release.sh` / `scripts/deploy.sh` / `scripts/rollback.sh`。部署历史存于 `releases/history.log`（纯文本，每行 `版本 时间 git_sha [rollback-from-xxx]`），供回滚解析。

### 5. 完整闭环示例
```bash
git tag v1.1.0 && git push origin v1.1.0      # 触发 CI release 作业 → 自动建 GitHub Release
make deploy v=1.1.0                            # 在目标机拉起 v1.1.0
# 出问题：
make rollback                                 # 自动回到 v1.0.0
```

> 接入远程仓库后才生效：`git remote add origin <url> && git push -u origin main --tags`。当前仓库已 `git init` 并提交 `v1.0.0` 基线。

