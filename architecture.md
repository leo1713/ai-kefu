# 技术架构文档

## 项目概览

**项目名称：** AI-CS（AI Customer Service）
**定位：** 面向小微电商的通用 AI 智能客服系统
**目标用户：** 日咨询量 0-50 人的电商企业
**部署方式：** 单服务器 Docker Compose 部署（云端 VPS 32G）

---

## 系统架构图

```
┌─────────────────────── 客户端层 ────────────────────────┐
│                                                          │
│  企业微信（主渠道）    网页聊天组件（备选）              │
│                                                          │
└────────────────────────┬─────────────────────────────────┘
                         │ HTTPS / WebSocket
                         ▼
┌─────────────────────── 接入层 ──────────────────────────┐
│                                                          │
│  Nginx（反向代理 + SSL + 限流）                         │
│                                                          │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
┌─────────────────────── 应用层 ──────────────────────────┐
│                                                          │
│  ai-cs-api（FastAPI，端口 8000）                        │
│  ├── 消息路由                                           │
│  ├── 访客管理                                           │
│  ├── 会话管理                                           │
│  ├── Agent 调度                                         │
│  ├── 工作流引擎                                         │
│  └── 管理后台 API                                       │
│                                                          │
└───────┬──────────┬──────────┬────────────────────────────┘
        │          │          │
        ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────────┐
│ Claude   │ │ RAG 模块 │ │ 工具执行器   │
│ API      │ │ (内置)   │ │ (支付/订单)  │
└──────────┘ └──────────┘ └──────────────┘

┌─────────────────────── 数据层 ──────────────────────────┐
│                                                          │
│  PostgreSQL 16 + pgvector    Redis 7                    │
│  （业务数据 + 向量数据）     （缓存 + 会话状态）        │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 技术选型

| 层面 | 技术 | 版本 | 选型理由 |
|------|------|------|----------|
| 语言 | Python | 3.11+ | AI 生态最完整，Claude SDK 原生支持 |
| Web 框架 | FastAPI | 0.115+ | 异步原生，SSE 支持，自动 API 文档 |
| ORM | SQLAlchemy | 2.0+ | 异步支持，类型安全，Alembic 迁移 |
| 数据库 | PostgreSQL | 16 | pgvector 向量搜索，JSON 支持 |
| 向量扩展 | pgvector | 0.7+ | 知识库 RAG，无需额外向量数据库 |
| 缓存 | Redis | 7 | 会话状态，消息队列，限流 |
| AI 模型 | Claude | Sonnet 4 | 工具调用稳定，中文好，性价比高 |
| 前端 | React + TypeScript | React 19 | 组件化，类型安全 |
| 构建工具 | Vite | 6+ | 快速构建，HMR |
| 样式 | TailwindCSS | 4 | 实用优先，开发效率高 |
| 状态管理 | Zustand | 5+ | 轻量，无样板代码 |
| 实时通信 | WebSocket | FastAPI 原生 | 客服工作台双向通信 |
| AI 流式 | SSE | FastAPI StreamingResponse | 访客端 AI 回复流式展示 |
| 异步任务 | Celery | 5+ | 文档处理，定时任务 |
| 容器化 | Docker Compose | v2 | 单机编排，一键部署 |
| 反向代理 | Nginx | 1.25+ | SSL，限流，静态资源 |

---

## 服务划分（单体 + 模块化）

不同于 TGO 的 10+ 微服务架构，本项目采用**单体应用 + 模块化设计**：

```
ai-cs/
├── backend/                    # 后端（单个 FastAPI 应用）
│   ├── app/
│   │   ├── main.py            # 应用入口
│   │   ├── config.py          # 配置管理
│   │   ├── database.py        # 数据库连接
│   │   │
│   │   ├── api/               # 路由层
│   │   │   ├── v1/
│   │   │   │   ├── chat.py         # 聊天接口
│   │   │   │   ├── agents.py       # Agent 管理
│   │   │   │   ├── knowledge.py    # 知识库管理
│   │   │   │   ├── visitors.py     # 访客管理
│   │   │   │   ├── conversations.py # 会话管理
│   │   │   │   ├── staff.py        # 客服管理
│   │   │   │   ├── workflows.py    # 工作流管理
│   │   │   │   └── admin.py        # 管理后台
│   │   │   └── internal/           # 内部接口（企业微信回调等）
│   │   │
│   │   ├── services/          # 业务逻辑层
│   │   │   ├── chat_service.py
│   │   │   ├── agent_service.py
│   │   │   ├── rag_service.py
│   │   │   ├── visitor_service.py
│   │   │   ├── conversation_service.py
│   │   │   ├── transfer_service.py    # 转人工逻辑
│   │   │   ├── workflow_service.py
│   │   │   └── wecom_service.py       # 企业微信
│   │   │
│   │   ├── models/            # 数据库模型（SQLAlchemy）
│   │   │   ├── visitor.py
│   │   │   ├── conversation.py
│   │   │   ├── message.py
│   │   │   ├── agent.py
│   │   │   ├── knowledge.py
│   │   │   ├── staff.py
│   │   │   └── workflow.py
│   │   │
│   │   ├── schemas/           # Pydantic 请求/响应模型
│   │   │
│   │   ├── ai/               # AI 核心模块
│   │   │   ├── agent_builder.py     # Agent 构建器
│   │   │   ├── agent_runner.py      # Agent 运行器
│   │   │   ├── tool_executor.py     # 工具执行器
│   │   │   ├── rag_engine.py        # RAG 检索引擎
│   │   │   ├── streaming.py         # SSE 流式输出
│   │   │   └── tools/              # 内置工具
│   │   │       ├── order_query.py       # 查订单
│   │   │       ├── refund_handler.py    # 退款处理
│   │   │       ├── payment_query.py     # 支付查询
│   │   │       ├── handoff.py          # 转人工
│   │   │       └── user_info.py        # 用户信息
│   │   │
│   │   ├── workflow/          # 工作流引擎
│   │   │   ├── engine.py
│   │   │   ├── graph.py
│   │   │   └── nodes/
│   │   │       ├── llm_node.py
│   │   │       ├── condition_node.py
│   │   │       ├── api_node.py
│   │   │       └── tool_node.py
│   │   │
│   │   ├── integrations/     # 外部集成
│   │   │   ├── wecom/             # 企业微信
│   │   │   │   ├── client.py
│   │   │   │   ├── callback.py
│   │   │   │   └── crypto.py
│   │   │   └── payment/           # 支付系统
│   │   │       └── client.py
│   │   │
│   │   └── core/             # 基础设施
│   │       ├── security.py        # JWT + 加密
│   │       ├── exceptions.py      # 统一异常
│   │       ├── logging.py         # 日志
│   │       └── middleware.py      # 中间件
│   │
│   ├── alembic/              # 数据库迁移
│   ├── tests/                # 测试
│   ├── pyproject.toml        # 依赖管理（Poetry）
│   └── Dockerfile
│
├── frontend/                  # 前端
│   ├── admin/                # 管理后台（React）
│   │   └── src/
│   │       ├── pages/
│   │       │   ├── Dashboard.tsx
│   │       │   ├── Agents.tsx
│   │       │   ├── Knowledge.tsx
│   │       │   ├── Conversations.tsx
│   │       │   ├── Visitors.tsx
│   │       │   ├── Staff.tsx
│   │       │   └── Workflows.tsx
│   │       ├── components/
│   │       └── stores/
│   │
│   └── widget/               # 网页聊天组件（React）
│       └── src/
│           ├── ChatWidget.tsx
│           ├── MessageList.tsx
│           └── stores/
│
├── docker-compose.yml         # 生产编排
├── docker-compose.dev.yml     # 开发环境
├── .env.example               # 配置模板
├── Makefile                   # 常用命令
├── AGENTS.md                  # Harness 约束规范
├── STATE.md                   # GSD 状态文件
└── README.md                  # 项目说明
```

---

## 为什么选单体而不是微服务

| 考虑因素 | 单体 | 微服务（TGO 模式） |
|----------|------|---------------------|
| 日咨询量 0-50 | ✅ 完全够用 | 过度设计 |
| 开发人数 1 人 | ✅ 简单 | 维护多个服务太复杂 |
| 部署成本 | ✅ 一台服务器 | 需要多台或 K8s |
| 调试难度 | ✅ 一个进程，断点直接打 | 跨服务调试困难 |
| 后续扩展 | 模块化设计，需要时可拆分 | 一开始就拆，前期浪费 |

**核心原则：模块化设计，单体部署，需要时再拆。**

---

## 数据流设计

### 访客发消息的完整链路

```
1. 企业微信推送消息到回调 URL
   POST /api/internal/wecom/callback

2. 验证签名，解密消息
   wecom_service.verify_and_decrypt()

3. 识别/创建访客
   visitor_service.get_or_create()

4. 检查 AI 状态
   ├── AI 已禁用 → 消息存储，等待人工
   └── AI 开启 → 继续

5. Agent 调度
   agent_service.dispatch(visitor, message)
   ├── 查询分析 → 选择合适的 Agent
   └── 执行 Agent

6. Agent 运行
   agent_runner.run(agent_config, message, history)
   ├── 加载系统提示词
   ├── 加载工具列表
   ├── 加载知识库上下文（RAG）
   ├── 调用 Claude API
   └── 处理工具调用循环

7. 返回结果
   ├── 企业微信 → 调用企微 API 发送回复
   └── 网页组件 → SSE 流式推送
```

### 人工接管链路

```
1. AI 判断需要转人工 / 访客主动要求
   → 调用 handoff 工具

2. transfer_service.transfer_to_staff()
   ├── 查找可用客服
   ├── 分配客服
   └── 标记访客 ai_disabled = True

3. 后续消息
   → WebSocket 推送到客服工作台
   → 客服在管理后台回复
   → 回复通过企业微信 API 发给访客
```

---

## 安全设计

| 安全项 | 实现方式 |
|--------|----------|
| API 认证 | JWT（管理后台）+ API Key（外部调用） |
| 企业微信回调验证 | 签名校验 + AES 解密 |
| API Key 存储 | Fernet 对称加密存 DB，.env 存主密钥 |
| 数据库密码 | .env 文件，不进 Git |
| HTTPS | Nginx + Let's Encrypt |
| 限流 | Redis 令牌桶，防刷接口 |
| SQL 注入防护 | SQLAlchemy 参数化查询 |
| XSS 防护 | React 默认转义 + CSP Header |
| CORS | 白名单域名 |

---

## 性能预估（单机 32G VPS）

| 指标 | 预估值 |
|------|--------|
| 同时在线访客 | 50-100 人 |
| 数据库连接池 | 10 + 20 overflow = 30 |
| AI 响应时间 | 首字 0.5-1s，完整 2-5s |
| 消息吞吐 | 200+ msg/min |
| 知识库文档量 | 1000+ 篇 |

对于日咨询 0-50 人的场景，单机完全够用。

---

## 扩展路径

当业务增长需要扩展时：

1. **咨询量到 100+/天** → 加 Redis 缓存热点数据
2. **咨询量到 500+/天** → 拆分 AI 模块为独立服务
3. **咨询量到 2000+/天** → 上 K8s，多实例部署
4. **多企业 SaaS 化** → 加 project_id 多租户隔离

---

## 开发环境要求

| 工具 | 版本 |
|------|------|
| Python | 3.11+ |
| Node.js | 22+ |
| Docker | 24+ |
| Docker Compose | v2 |
| Poetry | 1.8+ |
| Git | 2.40+ |

---

## 依赖的外部服务

| 服务 | 用途 | 是否必须 |
|------|------|----------|
| Claude API（Anthropic） | AI 对话、工具调用 | 必须 |
| 企业微信开放平台 | 客户消息收发 | 必须 |
| 支付系统 API | 查询支付状态、退款 | Phase 2 |
| Let's Encrypt | HTTPS 证书 | 部署时必须 |
