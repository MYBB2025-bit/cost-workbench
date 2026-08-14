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
