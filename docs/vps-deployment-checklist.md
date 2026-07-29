# Sprint 1.5.7 — VPS 部署前置检查清单

## 一、VPS 环境准备（首次部署）

### 1. VPS 基础信息确认

- [ ] VPS 公网 IP 地址：`_________________`
- [ ] 域名已解析到该 IP（A 记录）：`_________________`
- [ ] SSH 登录可用：`ssh user@<your-ip>`
- [ ] 操作系统：Ubuntu 22.04 / 24.04 或 Debian 11+

### 2. 初始化 VPS（运行一次）

```bash
# 在 VPS 上以 root 或 sudo 用户执行
sudo bash scripts/setup-vps.sh
```

**此脚本会：**
- 更新系统包
- 安装 Docker + Docker Compose
- 配置防火墙（开放 22/80/443 端口）
- 创建 `/opt/ai-cs` 部署目录

执行后**必须重新登录**以激活 docker 组权限。

---

## 二、代码和配置准备

### 3. 克隆代码仓库

```bash
cd /opt/ai-cs
git clone <your-repo-url> .
```

### 4. 配置环境变量

```bash
cp .env.example .env
nano .env  # 或用 vim
```

**必填项（生产环境）：**

| 变量 | 说明 | 示例 |
|------|------|------|
| `POSTGRES_PASSWORD` | PostgreSQL 数据库密码 | 随机强密码（20+字符） |
| `SECRET_KEY` | JWT 签名密钥 | 随机生成（见下方命令） |
| `ENCRYPTION_KEY` | Fernet 加密密钥 | 随机生成（见下方命令） |
| `ANTHROPIC_API_KEY` | Claude API Key | `sk-ant-api03-...` |

**可选项（推荐配置）：**

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `EMBEDDING_API_KEY` | 向量化 API Key（OpenAI/Voyage） | 未设置则降级到 ILIKE 搜索 |
| `EMBEDDING_MODEL` | 向量模型 | `text-embedding-3-small` |
| `WECOM_CORP_ID` | 企业微信 CorpID | Sprint 1.4 需要 |
| `WECOM_AGENT_ID` | 企业微信 AgentID | Sprint 1.4 需要 |
| `WECOM_SECRET` | 企业微信 Secret | Sprint 1.4 需要 |
| `WECOM_TOKEN` | 企业微信回调 Token | Sprint 1.4 需要 |
| `WECOM_ENCODING_AES_KEY` | 企业微信加密 Key | Sprint 1.4 需要 |

**生成随机密钥：**

```bash
# SECRET_KEY（64字符）
python3 -c "import secrets; print(secrets.token_urlsafe(48))"

# ENCRYPTION_KEY（Fernet 格式）
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 三、SSL 证书申请

### 5. 申请 Let's Encrypt 免费证书

```bash
bash scripts/init-ssl.sh <your-domain> <your-email>
```

**示例：**
```bash
bash scripts/init-ssl.sh ai-cs.example.com admin@example.com
```

**检查证书文件：**
```bash
ls -lh nginx/certs/
# 应该看到：fullchain.pem, privkey.pem
```

如果证书申请失败，确认：
- 域名 A 记录已生效（`dig <your-domain>`）
- 80 端口未被占用（`ss -tlnp | grep :80`）
- 防火墙允许 80 端口（`sudo ufw status`）

---

## 四、首次部署

### 6. 执行部署脚本

```bash
bash scripts/deploy.sh
```

**此脚本会：**
1. 拉取最新代码（`git pull`）
2. 构建前端（`npm ci && npm run build`）
3. 复制前端到 `nginx/html/`
4. 拉取并启动 Docker 容器
5. 运行数据库迁移（`alembic upgrade head`）

**预期输出：**
```
[1/5] 拉取代码...
[2/5] 构建前端...
[3/5] 构建并启动容器...
[4/5] 等待服务就绪...
[5/5] 运行数据库迁移...

部署完成！
```

---

## 五、部署验证

### 7. 健康检查

```bash
curl https://<your-domain>/health
```

**期望返回：**
```json
{"status":"ok","timestamp":"2026-07-29T09:00:00.000Z"}
```

### 8. 后端 API 验证

```bash
# 登录接口
curl -X POST https://<your-domain>/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

**期望返回：**
```json
{"access_token":"eyJ...","token_type":"bearer"}
```

### 9. 前端页面验证

浏览器访问：`https://<your-domain>/`

- [ ] 页面加载无 404（检查浏览器开发者工具 Console）
- [ ] 左侧导航栏显示正常
- [ ] 点击"对话记录"可见列表页（可能为空）
- [ ] 点击"Agent 管理"可见默认 Agent

### 10. SSE 流式对话验证（可选）

```bash
curl -N -X POST https://<your-domain>/api/v1/chat/completion \
  -H "Content-Type: application/json" \
  -d '{"message":"你好","visitor_id":"test-visitor"}'
```

**期望返回：** 逐行 SSE 事件流，包含 `chat.content_chunk` 和 `chat.completed`

---

## 六、生产运维命令

### 查看日志

```bash
# 所有服务
docker compose logs -f

# 仅后端
docker compose logs -f api

# 仅 nginx
docker compose logs -f nginx
```

### 重启服务

```bash
# 重启所有
docker compose restart

# 仅重启后端
docker compose restart api
```

### 停止服务

```bash
docker compose down
```

### 更新代码后重新部署

```bash
git pull
bash scripts/deploy.sh
```

---

## 七、常见问题排查

### 问题1：`curl /health` 超时

**可能原因：**
- Docker 容器未启动：`docker compose ps`
- 防火墙未开放 443：`sudo ufw status`
- Nginx 未正确代理：`docker compose logs nginx`

### 问题2：前端页面 404

**可能原因：**
- `nginx/html/` 为空：`ls -la nginx/html/`
- 前端构建失败：重新执行 `cd frontend/admin && npm run build`

### 问题3：数据库连接失败

**可能原因：**
- `.env` 中 `POSTGRES_PASSWORD` 与 docker-compose.yml 不一致
- PostgreSQL 容器未就绪：`docker compose ps postgres`

### 问题4：SSL 证书过期（90天后）

```bash
# 手动续期
bash scripts/init-ssl.sh <your-domain> <your-email>
docker compose restart nginx

# 或配置自动续期 cron
# 0 3 * * 1 cd /opt/ai-cs && bash scripts/init-ssl.sh <domain> <email> && docker compose restart nginx
```

---

## 八、Sprint 1.5.7 完成标志（三层验证）

- **层1（静态）：** `make check` 全通过（本地已验证 ✅）
- **层2（运行时）：** VPS 上 `curl https://<domain>/health` 返回 `{"status":"ok"}`
- **层3（端到端）：** 浏览器访问管理后台，对话列表/知识库/Agent 管理页面无报错

**完成后解除阻塞：** Sprint 1.4 企业微信回调验证可继续（需公网域名）

---

## 检查清单总览

```
VPS 部署前置检查
─────────────────────────────────────────────────
□ 1. VPS 可 SSH 登录
□ 2. 域名已解析到 VPS IP
□ 3. 执行 setup-vps.sh（首次）
□ 4. 重新登录激活 docker 组权限
□ 5. 克隆代码到 /opt/ai-cs
□ 6. 配置 .env（必填项：POSTGRES_PASSWORD, SECRET_KEY, ENCRYPTION_KEY, ANTHROPIC_API_KEY）
□ 7. 执行 init-ssl.sh 申请证书
□ 8. 执行 deploy.sh 部署
□ 9. curl /health 验证后端
□ 10. 浏览器访问验证前端
─────────────────────────────────────────────────
全部通过 → Sprint 1.5.7 ✅
```
