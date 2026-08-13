#!/usr/bin/env bash
# 发布编排：设定版本号 → 构建版本化镜像 → 生成发布说明 → 写入 CHANGELOG → 就绪部署。
# 用法：
#   bash scripts/release.sh 1.1.0      # 发布新版本（会写入 VERSION）
# 可选前置检查：取消下方注释可先跑本地 CI 再发布。
# 注意：本脚本只负责「构建 + 出说明」，真正的上线由 scripts/deploy.sh 完成。

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

NEWVER="${1:-}"
if [ -z "$NEWVER" ]; then
  echo "用法: bash scripts/release.sh <新版本号 如 1.1.0>" >&2
  exit 1
fi
NEWVER="${NEWVER#v}"

# （可选）发布前先跑本地 CI 守门
# bash scripts/ci.sh

# 1) 写入版本号
echo "$NEWVER" > VERSION
echo "==> 版本号已更新为 v${NEWVER}"

# 2) 构建版本化镜像（本地）
echo "==> 构建镜像 v${NEWVER}"
docker build -t "cost-backend:${NEWVER}"  -f cost_backend/Dockerfile cost_backend
docker build -t "cost-worker:${NEWVER}"   -f cost_backend/Dockerfile cost_backend
docker build -t "cost-flower:${NEWVER}"   -f cost_backend/Dockerfile cost_backend
docker build -t "cost-web:${NEWVER}"      -f cost_web/Dockerfile cost_web

# 同时打 latest 标签，便于本地 latest 部署
for s in backend worker flower web; do
  docker tag "cost-${s}:${NEWVER}" "cost-${s}:latest"
done
echo "✓ 镜像已构建并打标 :${NEWVER} / :latest"

# 3) 生成发布说明
bash scripts/gen-release-notes.sh "$NEWVER" > RELEASES.md
echo "✓ 发布说明已写入 RELEASES.md"

# 4) 追加到 CHANGELOG（保留历史）
if [ -f CHANGELOG.md ]; then
  { echo ""; cat RELEASES.md; } >> CHANGELOG.md
else
  cp RELEASES.md CHANGELOG.md
fi
echo "✓ 已更新 CHANGELOG.md"

# 5) 写 .env 的 IMAGE_TAG（指向新版本）
if [ -f .env ]; then
  grep -v '^IMAGE_TAG=' .env > .env.tmp && mv .env.tmp .env
else
  cp .env.example .env 2>/dev/null || touch .env
fi
echo "IMAGE_TAG=${NEWVER}" >> .env

echo
echo "🎉 发布 v${NEWVER} 就绪。下一步： bash scripts/deploy.sh ${NEWVER}"
echo "   回滚（如需）： bash scripts/rollback.sh"
