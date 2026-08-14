# 造价平台 v1.0.0

发布时间：2026-08-13
版本号：**1.0.0**

提交范围：首个提交以来全部
提交数量：**0** 个

## 变更摘要

- （无关联提交）

## 提交明细


## 部署方式

1. 拉取/构建版本化镜像后，使用版本标签启动：

```bash
IMAGE_TAG=1.0.0 docker compose up -d
```

2. 回滚到上一版本：

```bash
bash scripts/rollback.sh
```

> 完整发布闭环请见 README「发布流程闭环」章节。

# 造价平台 v1.0.1

发布时间：2026-08-14
版本号：**1.0.1**

提交范围：`v1.0.0..v1.0.1`
提交数量：**2** 个

## 变更摘要

- **其他**：变更 1 项
- **发布闭环**：变更 1 项

## 提交明细

- `63e54aa` fix: 补齐风险项创建/更新/删除接口 + 端到端功能冒烟测试
- `d6f13ee` docs(release): 初始化 CHANGELOG 与发布说明

## 部署方式

1. 拉取/构建版本化镜像后，使用版本标签启动：

```bash
IMAGE_TAG=1.0.1 docker compose up -d
```

2. 回滚到上一版本：

```bash
bash scripts/rollback.sh
```

> 完整发布闭环请见 README「发布流程闭环」章节。

# 造价平台 v1.0.2

发布时间：2026-08-14
版本号：**1.0.2**

提交范围：`v1.0.1..v1.0.2`
提交数量：**1** 个

## 变更摘要

- **发布闭环**：变更 1 项

## 提交明细

- `4ad81b5` chore: 记录 v1.0.1 部署历史

## 部署方式

1. 拉取/构建版本化镜像后，使用版本标签启动：

```bash
IMAGE_TAG=1.0.2 docker compose up -d
```

2. 回滚到上一版本：

```bash
bash scripts/rollback.sh
```

> 完整发布闭环请见 README「发布流程闭环」章节。

# 造价平台 v1.0.3

发布时间：2026-08-14
版本号：**1.0.3**

提交范围：`v1.0.2..v1.0.3`
提交数量：**1** 个

## 变更摘要

- **其他**：变更 1 项

## 提交明细

- `627cfbd` fix(deps): add missing openpyxl and bsdiff4 for tests; use sqlalchemy without deprecated async extra

## 部署方式

1. 拉取/构建版本化镜像后，使用版本标签启动：

```bash
IMAGE_TAG=1.0.3 docker compose up -d
```

2. 回滚到上一版本：

```bash
bash scripts/rollback.sh
```

> 完整发布闭环请见 README「发布流程闭环」章节。

# 造价平台 v1.0.4

发布时间：2026-08-14
版本号：**1.0.4**

提交范围：`v1.0.3..v1.0.4`
提交数量：**1** 个

## 变更摘要

- **数据迁移**：变更 1 项

## 提交明细

- `b2b2dea` fix(tests): skip migration preview when real 183MB data is absent; make CI smoke conditional

## 部署方式

1. 拉取/构建版本化镜像后，使用版本标签启动：

```bash
IMAGE_TAG=1.0.4 docker compose up -d
```

2. 回滚到上一版本：

```bash
bash scripts/rollback.sh
```

> 完整发布闭环请见 README「发布流程闭环」章节。

# 造价平台 v1.0.5

发布时间：2026-08-14
版本号：**1.0.5**

提交范围：`v1.0.4..v1.0.5`
提交数量：**1** 个

## 变更摘要

- **数据迁移**：变更 1 项

## 提交明细

- `94aacb3` fix(tests): import pytest in test_migration.py to satisfy ruff F821

## 部署方式

1. 拉取/构建版本化镜像后，使用版本标签启动：

```bash
IMAGE_TAG=1.0.5 docker compose up -d
```

2. 回滚到上一版本：

```bash
bash scripts/rollback.sh
```

> 完整发布闭环请见 README「发布流程闭环」章节。

# 造价平台 v1.0.6

发布时间：2026-08-14
版本号：**1.0.6**

提交范围：`v1.0.5..v1.0.6`
提交数量：**1** 个

## 变更摘要

- **BUG 修复（客户端更新）**：补丁上传接口 `POST /client/patch/upload` 的 `from_version`/`to_version` 由错误的 `Form(...)` 改回 `Query(...)`，与前端（`client.ts` 走 URL 查询串）及全部单测契约一致，修复 400 校验失败。
- **BUG 修复（历史数据迁移）**：`GET /migration/preview` 在迁移源文件缺失时由抛出 500 改为优雅返回 404，提升健壮性。
- **BUG 修复（风险项）**：`DELETE /risk/{id}` 返回体由 `{"ok": true}` 修正为 `{"deleted": true}`，与前端/单测预期一致。
- **工程（测试）**：`pyproject.toml` 增加 `[tool.pytest.ini_options] pythonpath = ["."]`，使 `pytest` 控制台脚本与 `python -m pytest` 两种调用均能解析内部包导入；新增 `scripts/functional_full.py` 全接口端到端测试（12 组 83 用例）。

## 提交明细

- `v1.0.6` fix: 修复补丁上传契约/迁移预览/风险删除返回，并补充全接口功能测试

## 部署方式

1. 拉取/构建版本化镜像后，使用版本标签启动：

```bash
IMAGE_TAG=1.0.6 docker compose up -d
```

2. 回滚到上一版本：

```bash
bash scripts/rollback.sh
```

> 完整发布闭环请见 README「发布流程闭环」章节。
