#!/bin/bash
# init-ssl.sh — 使用 Let's Encrypt 申请 SSL 证书
# 用法：bash scripts/init-ssl.sh <domain> <email>
set -e

DOMAIN="${1:?用法: $0 <domain> <email>}"
EMAIL="${2:?用法: $0 <domain> <email>}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p nginx/certs nginx/certbot

echo "正在为 $DOMAIN 申请 SSL 证书..."

# 如果 nginx 正在运行，先停止它（certbot standalone 需要 80 端口）
docker compose stop nginx 2>/dev/null || true

docker run --rm \
    -p 80:80 \
    -v "$ROOT_DIR/nginx/certs:/certs" \
    certbot/certbot certonly \
    --standalone \
    -d "$DOMAIN" \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    --cert-path /certs/cert.pem \
    --key-path /certs/privkey.pem \
    --fullchain-path /certs/fullchain.pem

echo ""
echo "证书已安装到 nginx/certs/"
echo "重启 nginx: docker compose up -d nginx"
