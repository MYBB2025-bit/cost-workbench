# 造价平台本地 CI 入口
# 用法： make            # 跑完整本地 CI
#       make backend     # 仅后端
#       make frontend    # 仅前端
#       make docker      # 构建两个镜像（需本机 docker）
# 发布闭环：
#       make release v=1.1.0   # 升版 + 构建镜像 + 生成发布说明
#       make deploy  v=1.1.0   # 按版本拉起（docker compose up -d）
#       make rollback          # 回退到上一部署版本

PYTHON ?= python3

backend:
	cd cost_backend && $(PYTHON) -m ruff check .
	cd cost_backend && $(PYTHON) -m pytest tests -q

frontend:
	cd cost_web && npm ci
	cd cost_web && npm run build

ci: backend frontend
	@echo "✅ 本地 CI 全部通过"

docker:
	docker build -t cost-backend:local -f cost_backend/Dockerfile cost_backend
	docker build -t cost-web:local -f cost_web/Dockerfile cost_web

release:
	bash scripts/release.sh $(v)

deploy:
	bash scripts/deploy.sh $(v)

rollback:
	bash scripts/rollback.sh

.PHONY: backend frontend ci docker release deploy rollback
