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

- **BUG 修复**：变更 3 项（补丁上传契约、迁移预览、风险删除返回）
- **工程**：变更 1 项（pytest pythonpath + 全接口功能测试）

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
