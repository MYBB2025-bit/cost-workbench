#!/usr/bin/env bash
# 生成发布说明（Markdown），输出到 stdout。
# 用法：
#   bash scripts/gen-release-notes.sh            # 使用 VERSION 文件 / git describe
#   bash scripts/gen-release-notes.sh 1.2.0      # 显式指定版本
#   bash scripts/gen-release-notes.sh 1.2.0 > RELEASES.md
#
# 逻辑：取上一 tag 到当前版本的 git 提交，按关键字归纳到平台模块（Celery / Loki /
#       前端增强 / CI / 数据迁移 / 发布闭环 / 其他），并列出提交明细。
# 非 git 环境下退化为仅输出版本与日期。

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# ---------------- 版本号 ----------------
VERSION="${1:-}"
if [ -z "$VERSION" ]; then
  if [ -f VERSION ]; then
    VERSION="$(cat VERSION | tr -d '[:space:]')"
  fi
fi
if [ -z "$VERSION" ]; then
  VERSION="$(git describe --tags --always 2>/dev/null | tr -d '[:space:]')"
fi
VERSION="${VERSION#v}"   # 去掉可能的前缀 v

DATE="$(date +%Y-%m-%d)"

# ---------------- 是否 git 仓库 ----------------
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  IS_GIT=1
else
  IS_GIT=0
fi

echo "# 造价平台 v${VERSION}"
echo
echo "发布时间：${DATE}"
echo "版本号：**${VERSION}**"
echo

if [ "$IS_GIT" -eq 1 ]; then
  # 上一 tag（排除当前版本本身）
  PREV="$(git tag --sort=-creatordate | grep -v "^v\?${VERSION}$" | head -1 || true)"
  if [ -n "$PREV" ]; then
    RANGE="${PREV}..HEAD"
    echo "提交范围：\`${PREV}..v${VERSION}\`"
  else
    RANGE="$(git rev-list --max-parents=0 HEAD)..HEAD"
    echo "提交范围：首个提交以来全部"
  fi

  COUNT="$(git rev-list --count "$RANGE" 2>/dev/null || echo 0)"
  echo "提交数量：**${COUNT}** 个"
  echo

  # ---------------- 按模块归纳 ----------------
  echo "## 变更摘要"
  echo

  # 模块关键词 → 标签
  declare -A MODULES=(
    ["celery|异步|worker|任务队列"]="异步任务 (Celery)"
    ["loki|日志聚合|logging"]="日志聚合 (Loki)"
    ["前端|vue|dashboard|echarts|页面|组件"]="前端增强"
    ["ci|流水线|github actions|workflow|ruff|pytest"]="CI 流水线"
    ["迁移|migrat|183|数据导入|user-data"]="数据迁移"
    ["发布|release|部署|回滚|deploy|rollback|VERSION|镜像|compose"]="发布闭环"
  )

  # 统计每个模块的提交数
  declare -A HITS
  while IFS= read -r line; do
    subject="${line#* }"
    matched=0
    for pat in "${!MODULES[@]}"; do
      if printf '%s' "$subject" | grep -Eiq "$pat"; then
        label="${MODULES[$pat]}"
        HITS["$label"]=$(( ${HITS["$label"]:-0} + 1 ))
        matched=1
        break
      fi
    done
    if [ "$matched" -eq 0 ]; then
      HITS["其他"]=$(( ${HITS["其他"]:-0} + 1 ))
    fi
  done < <(git log --pretty="%h %s" "$RANGE")

  if [ "${#HITS[@]}" -eq 0 ]; then
    echo "- （无关联提交）"
  else
    for label in "${!HITS[@]}"; do
      echo "- **${label}**：变更 ${HITS[$label]} 项"
    done
  fi
  echo

  # ---------------- 提交明细 ----------------
  echo "## 提交明细"
  echo
  git log --pretty="- \`%h\` %s" "$RANGE"
  echo
else
  echo "（当前目录非 git 仓库，跳过提交历史归纳。）"
  echo
fi

# ---------------- 部署指引 ----------------
echo "## 部署方式"
echo
echo "1. 拉取/构建版本化镜像后，使用版本标签启动："
echo
echo '```bash'
echo "IMAGE_TAG=${VERSION} docker compose up -d"
echo '```'
echo
echo "2. 回滚到上一版本："
echo
echo '```bash'
echo "bash scripts/rollback.sh"
echo '```'
echo
echo "> 完整发布闭环请见 README「发布流程闭环」章节。"
