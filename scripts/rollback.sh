#!/usr/bin/env bash
# 一键回滚：退回到上一次部署的版本并重新拉起。
# 用法：
#   bash scripts/rollback.sh
# 前置：releases/history.log 至少含有两次部署记录（由 deploy.sh 写入）。

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HISTORY="releases/history.log"
if [ ! -f "$HISTORY" ]; then
  echo "❌ 无部署历史（$HISTORY 不存在），无法回滚" >&2
  exit 1
fi

LINES="$(wc -l < "$HISTORY" | tr -d ' ')"
if [ "$LINES" -lt 2 ]; then
  echo "❌ 部署历史不足两次，无法回滚（当前仅 $(grep -c . "$HISTORY") 条）" >&2
  exit 1
fi

# 最后一行是当前版本，倒数第二行是上一版本
CUR="$(tail -n 1 "$HISTORY" | awk '{print $1}')"
PREV="$(tail -n 2 "$HISTORY" | head -n 1 | awk '{print $1}')"

if [ -z "$PREV" ] || [ "$PREV" = "$CUR" ]; then
  echo "❌ 未能解析出有效的回滚目标版本" >&2
  exit 1
fi

echo "==> 回滚：v${CUR} -> v${PREV}"

# 写 IMAGE_TAG 到 .env
if [ -f .env ]; then
  grep -v '^IMAGE_TAG=' .env > .env.tmp 2>/dev/null || true
  mv .env.tmp .env
else
  cp .env.example .env 2>/dev/null || touch .env
fi
echo "IMAGE_TAG=${PREV}" >> .env

# 若配置了镜像仓库，则先拉取
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi
if [ -n "${DOCKER_REGISTRY:-}" ]; then
  docker compose pull
fi

docker compose up -d

# 记录回滚事件
SHA="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
TS="$(date +%Y-%m-%dT%H:%M:%S%z)"
echo "${PREV} ${TS} ${SHA} rollback-from-${CUR}" >> "$HISTORY"

echo
echo "✅ 已回滚到 v${PREV}。访问 http://localhost"
echo "    最近部署历史："
tail -n 5 "$HISTORY"
