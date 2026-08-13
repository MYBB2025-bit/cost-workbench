#!/usr/bin/env bash
# 本地 CI 一键脚本：复刻 GitHub Actions 的 backend + frontend 检查。
# 用法：
#   bash scripts/ci.sh                 # 完整跑（含 npm ci）
#   SKIP_NPM_INSTALL=1 bash scripts/ci.sh   # 复用已装 node_modules，仅构建
# 可覆盖解释器： PYTHON=/path/to/python3 bash scripts/ci.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-${PYTHON3:-python3}}"

echo "==> 使用 Python: $($PYTHON --version 2>&1)"
echo "==> 仓库根目录: $ROOT"
echo

# ---------------- 后端：ruff lint + pytest ----------------
echo "=================================================="
echo "[1/2] 后端：ruff 静态检查"
echo "=================================================="
cd "$ROOT/cost_backend"
"$PYTHON" -m ruff check .
echo "✓ ruff 通过"
echo

echo "=================================================="
echo "[1/2] 后端：pytest 测试"
echo "=================================================="
# 与 CI 一致的测试环境变量（conftest 也会兜底）
export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///./test_cost.db}"
export USE_LOCAL_STORAGE="${USE_LOCAL_STORAGE:-true}"
export SECRET_KEY="${SECRET_KEY:-test-secret-key}"
export INIT_ADMIN_USERNAME="${INIT_ADMIN_USERNAME:-admin}"
export INIT_ADMIN_PASSWORD="${INIT_ADMIN_PASSWORD:-admin123}"
export MINIO_BUCKET_PATCH="${MINIO_BUCKET_PATCH:-cost-patch}"
export CELERY_TASK_ALWAYS_EAGER="${CELERY_TASK_ALWAYS_EAGER:-1}"
export CELERY_TASK_EAGER_PROPAGATES="${CELERY_TASK_EAGER_PROPAGATES:-1}"
"$PYTHON" -m pytest tests -q
echo

# ---------------- 前端：类型检查 + 构建 ----------------
echo "=================================================="
echo "[2/2] 前端：install + build (vue-tsc + vite)"
echo "=================================================="
cd "$ROOT/cost_web"
if [ "${SKIP_NPM_INSTALL:-0}" != "1" ]; then
  npm ci
else
  echo "(SKIP_NPM_INSTALL=1) 跳过 npm 安装，复用现有 node_modules"
fi
npm run build
echo

echo "=================================================="
echo "✅ 本地 CI 全部通过"
echo "=================================================="
