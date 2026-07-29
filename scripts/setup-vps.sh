#!/bin/bash
# setup-vps.sh — VPS 初始化（Ubuntu/Debian）
# 用法：bash scripts/setup-vps.sh
set -e

echo "=============================="
echo "  VPS 初始化"
echo "=============================="

# 1. 更新系统
apt-get update -qq && apt-get upgrade -y -qq

# 2. 安装基础工具
apt-get install -y git curl wget ufw

# 3. 安装 Docker
if ! command -v docker &>/dev/null; then
    echo "安装 Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    # 将当前用户加入 docker 组
    usermod -aG docker "${SUDO_USER:-$USER}"
    echo "Docker 安装完成"
fi

# 4. 配置防火墙
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP
ufw allow 443/tcp  # HTTPS
ufw --force enable
echo "防火墙已配置（22/80/443）"

# 5. 创建部署目录
mkdir -p /opt/ai-cs
chown "${SUDO_USER:-$USER}:${SUDO_USER:-$USER}" /opt/ai-cs

echo ""
echo "=============================="
echo "  VPS 初始化完成！"
echo ""
echo "  下一步："
echo "  1. 重新登录以激活 docker 组权限"
echo "  2. cd /opt/ai-cs && git clone <your-repo-url> ."
echo "  3. cp .env.example .env && nano .env（填写配置）"
echo "  4. bash scripts/init-ssl.sh <your-domain> <email>"
echo "  5. bash scripts/deploy.sh"
echo "=============================="
