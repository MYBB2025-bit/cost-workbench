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
