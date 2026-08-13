#!/usr/bin/env bash
# 一键部署：把指定版本镜像拉起（docker compose up -d），并记录部署历史。
# 用法：
#   bash scripts/deploy.sh            # 部署 VERSION 文件中的版本
#   bash scripts/deploy.sh 1.0.0     # 部署指定版本
# 前置：release.sh 已构建好版本化镜像，或镜像可从 DOCKER_REGISTRY 拉取。

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# 读取 .env（若存在）以获知 IMAGE_TAG / DOCKER_REGISTRY
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

VERSION="${1:-${IMAGE_TAG:-}}"
if [ -z "$VERSION" ]; then
  if [ -f VERSION ]; then
    VERSION="$(cat VERSION | tr -d '[:space:]')"
  fi
fi
if [ -z "$VERSION" ]; then
  echo "❌ 无法确定部署版本：请传参或确保 VERSION / .env 的 IMAGE_TAG 已设置" >&2
  exit 1
fi
VERSION="${VERSION#v}"

# 写 IMAGE_TAG 到 .env（供 docker compose 读取）
mkdir -p releases
if [ -f .env ]; then
  grep -v '^IMAGE_TAG=' .env > .env.tmp 2>/dev/null || true
  mv .env.tmp .env
else
  cp .env.example .env 2>/dev/null || touch .env
fi
echo "IMAGE_TAG=${VERSION}" >> .env

# 记录部署历史（纯文本： version timestamp sha）
SHA="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
TS="$(date +%Y-%m-%dT%H:%M:%S%z)"
echo "${VERSION} ${TS} ${SHA}" >> releases/history.log

echo "==> 部署版本 v${VERSION} (git_sha=${SHA})"

# 若配置了镜像仓库，则先拉取；否则使用本地已构建镜像
if [ -n "${DOCKER_REGISTRY:-}" ]; then
  echo "--> 从仓库 ${DOCKER_REGISTRY} 拉取镜像"
  docker compose pull
fi

docker compose up -d
echo
echo "✅ 已部署 v${VERSION}。访问 http://localhost （前端 80 / 后端 8000 / Grafana 3000）"
echo "    部署历史："
tail -n 5 releases/history.log
