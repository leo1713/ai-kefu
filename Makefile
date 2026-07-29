.DEFAULT_GOAL := help

POETRY := $(shell command -v poetry 2>/dev/null || echo $(HOME)/.local/bin/poetry)

.PHONY: help setup dev dev-watch down docker-dev test lint check migrate clean \
        deploy prod-logs prod-migrate ssl-init

help: ## 显示帮助信息
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## 安装所有依赖，初始化数据库
	cd backend && $(POETRY) install
	@if [ ! -f .env ]; then cp .env.example .env; echo "已创建 .env，请填写必要配置"; fi

dev: ## 启动完整开发环境（需代理：export http_proxy=http://127.0.0.1:7897）
	docker compose -f docker-compose.dev.yml up -d --build

dev-local: ## 本地启动 API（无需 Docker，用于无代理环境）
	@kill $$(lsof -ti:8000) 2>/dev/null || true
	cd backend && $(POETRY) run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
	@echo "Waiting for API on :8000..."; \
	for i in $$(seq 1 20); do \
	  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then \
	    echo "API is up"; break; \
	  fi; \
	  sleep 0.5; \
	done

dev-watch: ## 前台启动 API（带日志输出）
	cd backend && $(POETRY) run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

docker-dev: ## 同 dev（别名）
	docker compose -f docker-compose.dev.yml up -d --build

down: ## 停止本地 API 进程
	-kill $$(lsof -ti:8000) 2>/dev/null; echo "API stopped"

docker-down: ## 停止 Docker 服务
	docker compose -f docker-compose.dev.yml down

logs: ## 查看 Docker API 日志（开发）
	docker compose -f docker-compose.dev.yml logs -f api

test: ## 运行全部测试
	cd backend && $(POETRY) run pytest

lint: ## 代码规范检查
	cd backend && $(POETRY) run ruff check .
	cd backend && $(POETRY) run mypy --strict app/

check: ## 完整验证（lint + test）
	cd backend && $(POETRY) run ruff check .
	cd backend && $(POETRY) run mypy --strict app/
	cd backend && $(POETRY) run pytest
	bash scripts/check-arch.sh

migrate: ## 运行数据库迁移（开发）
	docker compose -f docker-compose.dev.yml run --rm api alembic upgrade head

migration: ## 生成新迁移文件（用法：make migration MSG="描述"）
	docker compose -f docker-compose.dev.yml run --rm api alembic revision --autogenerate -m "$(MSG)"

shell: ## 进入 API 容器 shell
	docker compose -f docker-compose.dev.yml exec api bash

clean: ## 清理 Docker 资源
	docker compose -f docker-compose.dev.yml down -v --remove-orphans

# ── 生产部署 ──────────────────────────────────────────────────────────────────

deploy: ## 生产部署（构建前端+启动容器+迁移数据库）
	bash scripts/deploy.sh

ssl-init: ## 申请 SSL 证书（用法：make ssl-init DOMAIN=your.com EMAIL=you@email.com）
	bash scripts/init-ssl.sh $(DOMAIN) $(EMAIL)

prod-migrate: ## 生产数据库迁移
	docker compose run --rm api alembic upgrade head

prod-logs: ## 查看生产日志
	docker compose logs -f api nginx

