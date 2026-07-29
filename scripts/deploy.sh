#!/bin/bash
# deploy.sh — 生产部署脚本
# 用法：bash scripts/deploy.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

echo "=============================="
echo "  AI-CS 生产部署"
echo "=============================="

# 前置检查
[ -f .env ] || { echo "ERROR: .env 不存在，先执行: cp .env.example .env"; exit 1; }
[ -f nginx/certs/fullchain.pem ] || echo "WARNING: SSL 证书未找到，运行 bash scripts/init-ssl.sh <domain> <email> 后重启 nginx"

# 1. 拉取最新代码
echo "[1/5] 拉取代码..."
git pull

# 2. 构建前端
echo "[2/5] 构建前端..."
cd frontend/admin
npm ci --silent
npm run build
cd "$ROOT_DIR"
mkdir -p nginx/html
cp -r frontend/admin/dist/* nginx/html/
echo "    -> 前端已构建并复制到 nginx/html/"

# 3. 构建并启动容器
echo "[3/5] 构建并启动容器..."
docker compose pull --quiet
docker compose up -d --build

# 4. 等待数据库就绪
echo "[4/5] 等待服务就绪..."
sleep 8

# 5. 运行迁移
echo "[5/5] 运行数据库迁移..."
docker compose run --rm api alembic upgrade head

echo ""
echo "=============================="
echo "  部署完成！"
echo ""
echo "  健康检查: curl https://your-domain.com/health"
echo "  查看日志: make prod-logs"
echo "=============================="
