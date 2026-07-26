# GSD Phase 计划

## 项目状态

- **当前 Phase：** Phase 1 — MVP
- **Phase 1 状态：** 未开始
- **整体进度：** 0%

---

## Phase 总览

| Phase | 名称 | 目标 | 预估周期 | 状态 |
|-------|------|------|----------|------|
| 1 | MVP | 企业微信 + AI 知识库问答，能真实使用 | 4-6 周 | 🔴 未开始 |
| 2 | 人工协作 | 转人工 + 客服工作台 + 工具调用 | 3-4 周 | ⬜ 等待 |
| 3 | 智能增强 | 多 Agent + 工作流 + 数据看板 | 3-4 周 | ⬜ 等待 |

---

## Phase 1：MVP — 详细任务分解

### 目标

客户在企业微信发问题 → AI 基于知识库回答 → 对话记录可查看。

### 完成标志

- [ ] 企业微信发消息，3秒内收到 AI 回复
- [ ] AI 回复内容基于上传的文档（不是瞎编的）
- [ ] 管理后台可以看到所有对话记录
- [ ] `make check` 全部通过

---

### Sprint 1.1：项目骨架（第1周）

**目标：** 项目结构搭建完成，能本地启动，空接口能跑通。

| ID | 行为描述 | 验证命令 | 状态 |
|----|---------|---------|------|
| 1.1.1 | 后端项目可本地启动（Poetry + FastAPI + 目录结构） | `make dev && curl -f http://localhost:8000/health` | ✅ |
| 1.1.2 | 前端项目可本地启动（Vite + React + TypeScript + Tailwind） | `cd frontend/admin && npm run build` | ✅ |
| 1.1.3 | Docker Compose 编排所有服务（PostgreSQL + Redis + 后端 + 前端） | `make dev && docker compose ps \| grep -c "Up" \| grep -q "4"` | ✅ |
| 1.1.4 | 数据库连接 + 基础模型建表（Visitor, Message, Conversation） | `make migrate && cd backend && python -c "from app.models import Visitor; print('OK')"` | ✅ |
| 1.1.5 | 健康检查接口 `GET /health` 返回 200 | `curl -sf http://localhost:8000/health \| python -c "import sys,json; d=json.load(sys.stdin); assert d['status']=='ok'"` | ✅ |
| 1.1.6 | Makefile 所有命令可执行 | `make help` 或逐条执行 setup/dev/test/lint/check | ✅ |
| 1.1.7 | `make check` 全部通过（lint + type + test） | `make check` 退出码为 0 | ✅ |

> **状态说明：** ⬜ 未开始 · 🔄 进行中 · 🚫 阻塞（见遗留问题） · ✅ 已完成

**Sprint 1.1 完成标志（三层验证）：**
- 层1（静态）：`make check` 全通过
- 层2（运行时）：`make dev` 启动，`/health` 返回 `{"status":"ok"}`
- 层3（端到端）：`bash scripts/check-arch.sh` 无违规

---

### Sprint 1.2：AI 对话核心（第2周）

**目标：** 通过 API 发送消息，Claude 返回回复（无知识库，纯对话）。

| ID | 行为描述 | 验证命令 | 状态 |
|----|---------|---------|------|
| 1.2.1 | Claude SDK 集成，单元测试 Mock 通过 | `cd backend && pytest tests/unit/test_ai/ -v` | ⬜ |
| 1.2.2 | Agent 模型和配置，seed 默认 Agent 写入数据库 | `cd backend && pytest tests/integration/test_api/test_agents.py -v` | ⬜ |
| 1.2.3 | `POST /api/v1/chat/completion` 返回流式回复 | `curl -sf -X POST http://localhost:8000/api/v1/chat/completion -d '{"message":"你好","visitor_id":"test"}' \| grep "chat.completed"` | ⬜ |
| 1.2.4 | SSE 流式响应前端可逐字显示 | 浏览器打开测试页，输入消息可见逐字输出 | ⬜ |
| 1.2.5 | 消息历史写入数据库 | `cd backend && pytest tests/integration/test_api/test_chat.py::test_message_persisted -v` | ⬜ |
| 1.2.6 | 连续对话能记住上下文（最近10轮） | `cd backend && pytest tests/unit/test_services/test_chat_service.py::test_context_memory -v` | ⬜ |
| 1.2.7 | API Key 无效/超时返回统一错误格式 | `cd backend && pytest tests/unit/test_services/test_chat_service.py::test_error_handling -v` | ⬜ |

> **状态说明：** ⬜ 未开始 · 🔄 进行中 · 🚫 阻塞（见遗留问题） · ✅ 已完成

**Sprint 1.2 完成标志（三层验证）：**
- 层1（静态）：`make check` 全通过
- 层2（运行时）：`POST /api/v1/chat/completion` 流式收到 Claude 回复，数据库有消息记录
- 层3（端到端）：连续发 3 条消息，第 3 条能引用前 2 条内容回答

---

### Sprint 1.3：知识库 RAG（第3周）

**目标：** 上传文档后，AI 回答基于文档内容。

| ID | 行为描述 | 验证命令 | 状态 |
|----|---------|---------|------|
| 1.3.1 | pgvector 扩展启用，向量表迁移通过 | `make migrate && cd backend && python -c "from app.models import KnowledgeChunk; print('OK')"` | ⬜ |
| 1.3.2 | `POST /api/v1/knowledge/upload` 接受 PDF/TXT/MD 文件 | `curl -sf -F "file=@tests/fixtures/sample.pdf" http://localhost:8000/api/v1/knowledge/upload \| python -c "import sys,json; assert json.load(sys.stdin)['id']"` | ⬜ |
| 1.3.3 | 文档自动分片，一篇文档切成多个 chunk | `cd backend && pytest tests/unit/test_services/test_rag_service.py::test_document_chunking -v` | ⬜ |
| 1.3.4 | chunk 向量化写入 pgvector | `cd backend && pytest tests/integration/test_api/test_knowledge.py::test_embedding_stored -v` | ⬜ |
| 1.3.5 | `GET /api/v1/knowledge/search?q=xxx` 返回相关 chunk | `curl -sf "http://localhost:8000/api/v1/knowledge/search?q=退款" \| python -c "import sys,json; assert len(json.load(sys.stdin)['results'])>0"` | ⬜ |
| 1.3.6 | 聊天时 AI 回答引用知识库内容 | `cd backend && pytest tests/integration/test_api/test_chat.py::test_rag_grounded_answer -v` | ⬜ |
| 1.3.7 | 知识库 CRUD 接口可用（集合增删改查） | `cd backend && pytest tests/integration/test_api/test_knowledge.py -v` | ⬜ |

> **状态说明：** ⬜ 未开始 · 🔄 进行中 · 🚫 阻塞（见遗留问题） · ✅ 已完成

**Sprint 1.3 完成标志（三层验证）：**
- 层1（静态）：`make check` 全通过
- 层2（运行时）：上传 sample.pdf，`/knowledge/search?q=退款` 返回非空结果
- 层3（端到端）：`POST /chat/completion` 问"退款政策是什么"，回复中包含文档内容（非通用泛答）

---

### Sprint 1.4：企业微信接入（第4周）

**目标：** 企业微信发消息 → 系统收到 → AI 回复 → 通过企业微信发回。

| ID | 行为描述 | 验证命令 | 状态 |
|----|---------|---------|------|
| 1.4.1 | 企业微信应用注册，获取 CorpID/AgentID/Secret | 人工验证：企业微信后台可见应用 | ⬜ |
| 1.4.2 | `GET /api/internal/wecom/callback` 签名校验通过 | `cd backend && pytest tests/integration/test_wecom/test_callback.py::test_verify_url -v` | ⬜ |
| 1.4.3 | `POST /api/internal/wecom/callback` 解密接收消息 | `cd backend && pytest tests/integration/test_wecom/test_callback.py::test_receive_message -v` | ⬜ |
| 1.4.4 | 系统通过企业微信 API 发送文本回复 | `cd backend && pytest tests/integration/test_wecom/test_callback.py::test_send_reply -v` | ⬜ |
| 1.4.5 | 相同 external_userid 的消息关联到同一 Visitor | `cd backend && pytest tests/unit/test_services/test_visitor_service.py::test_get_or_create -v` | ⬜ |
| 1.4.6 | 图片消息能被识别并生成 AI 回复 | `cd backend && pytest tests/integration/test_wecom/test_callback.py::test_image_message -v` | ⬜ |
| 1.4.7 | 相同 MsgId 不重复处理（去重） | `cd backend && pytest tests/unit/test_services/test_wecom_service.py::test_dedup -v` | ⬜ |

> **状态说明：** ⬜ 未开始 · 🔄 进行中 · 🚫 阻塞（见遗留问题） · ✅ 已完成

**Sprint 1.4 完成标志（三层验证）：**
- 层1（静态）：`make check` 全通过
- 层2（运行时）：企业微信后台回调 URL 验证通过
- 层3（端到端）：在企业微信发"你们怎么退款"，3秒内收到基于知识库的 AI 回复

---

### Sprint 1.5：管理后台基础（第5-6周）

**目标：** 基础管理界面可用，能查看对话和管理知识库。

| ID | 行为描述 | 验证命令 | 状态 |
|----|---------|---------|------|
| 1.5.1 | `POST /api/v1/auth/login` 返回 JWT token | `cd backend && pytest tests/integration/test_api/test_auth.py -v` | ⬜ |
| 1.5.2 | 对话列表页面显示所有会话 | 浏览器访问 `/conversations`，页面无报错，列表可见 | ⬜ |
| 1.5.3 | 对话详情页面显示完整消息时间线 | 浏览器点击某会话，消息按时间排列显示 | ⬜ |
| 1.5.4 | 知识库管理页面可上传/删除文档 | 浏览器上传一个 .txt 文件，列表中出现该文档 | ⬜ |
| 1.5.5 | Agent 配置页面保存提示词后生效 | 修改提示词保存，重新发消息，AI 回复风格改变 | ⬜ |
| 1.5.6 | 系统设置页面保存 API Key，加密存储 | `cd backend && pytest tests/integration/test_api/test_admin.py::test_api_key_encrypted -v` | ⬜ |
| 1.5.7 | Nginx + Docker 部署，VPS 上可访问 | `curl -sf https://<域名>/health \| grep ok` | ⬜ |

> **状态说明：** ⬜ 未开始 · 🔄 进行中 · 🚫 阻塞（见遗留问题） · ✅ 已完成

**Sprint 1.5 完成标志（三层验证）：**
- 层1（静态）：`make check` 全通过
- 层2（运行时）：管理后台可登录，对话列表和知识库页面无报错
- 层3（端到端）：从企业微信发消息 → 管理后台可见该对话记录

---

## Phase 2：人工协作 — 任务概要

> Phase 1 完成后再细化

| Sprint | 目标 | 核心任务 |
|--------|------|----------|
| 2.1 | 转人工机制 | handoff 工具、AI 禁用标记、客服分配 |
| 2.2 | 客服工作台 | WebSocket 实时通信、会话列表、回复功能 |
| 2.3 | 工具调用 | 订单查询、支付查询、物流查询集成 |
| 2.4 | 访客管理 | 标签系统、信息完善、搜索筛选 |

---

## Phase 3：智能增强 — 任务概要

> Phase 2 完成后再细化

| Sprint | 目标 | 核心任务 |
|--------|------|----------|
| 3.1 | 多 Agent | 分诊 Agent、专业 Agent、路由逻辑 |
| 3.2 | QA 知识库 | 精确匹配、批量导入 |
| 3.3 | 工作流引擎 | DAG 执行器、节点类型、可视化编辑 |
| 3.4 | 数据看板 | 统计接口、图表组件 |

---

## GSD 工作节奏

每个 Sprint 遵循 GSD 5 步循环：

```
/gsd-discuss  → 讨论这个 Sprint 的实现方案
/gsd-plan     → 分解任务，确认完成标准
/gsd-execute  → 写代码（遵守 AGENTS.md 规范）
/gsd-verify   → 跑 verify.sh，确认全部通过
/gsd-ship     → 提交代码，更新 STATE.md 进度
```

### 每个任务的完成定义

一个任务标记为 ✅ 的条件：

1. 代码已写完
2. 有对应的测试（单元或集成）
3. `make check` 通过（lint + type + test）
4. 功能可演示（能看到效果）

---

## 会话生命周期

### 会话开始（接班）

新会话开始时，AI 必须按顺序执行：

1. 读 `AGENTS.md` — 确认编码约束
2. 读 `STATE.md` 本文件 — 确认当前 Sprint 和上次进度
3. 读"上次会话记录"区块 — 了解遗留问题和下一步
4. 如果项目已有代码：运行 `make check` — 确认环境健康
5. 从"下一步行动"中的第一条开始执行，不重新规划已完成的工作

> 目标：3 分钟内恢复到可执行状态，不重复上一个会话的探索工作。

### 任务状态使用规则

| 状态 | 含义 | 何时设置 |
|------|------|----------|
| ⬜ | 未开始 | 默认状态 |
| 🔄 | 进行中 | 开始动手的第一步就改为此状态，WIP=1 |
| 🚫 | 阻塞 | 遇到外部依赖/无法独立解决的问题，在遗留问题中注明原因 |
| ✅ | 已完成 | 三层验证全部通过后才能设为此状态 |

**规则：**
- 任意时刻最多只有 **1 个** 🔄 进行中的任务
- 🚫 阻塞的任务必须在"遗留问题"区块写明阻塞原因和解除条件
- ✅ 不可逆：已通过验证的任务不会退回到 ⬜

### 会话结束（交班）

每个会话结束前，必须完成以下清洁退出检查清单：

```
会话退出检查清单
─────────────────────────────────────────
□ 1. make check 通过（lint + type + test）
□ 2. 正在进行的任务状态已更新（🔄 或标回 ⬜）
□ 3. 遗留问题已记录（阻塞原因 + 解除条件）
□ 4. 下一步行动已写清楚（下个会话可直接开始）
□ 5. 无调试代码残留（console.log / print / TODO）
□ 6. git commit 已提交，repo 处于可恢复状态
─────────────────────────────────────────
全部勾选才算交班完成。
```

---

## 上次会话记录

> 每次会话结束时更新此区块。新会话开始时先读此区块。

**最后更新：** 2026-07-26  
**当前 Sprint：** Sprint 1.1 全部完成 ✅  
**测试状态：** 1 passed（tests/unit/test_health.py），make check 全绿

### 本次完成

- 任务1.1.1 ✅：Poetry + FastAPI 后端初始化，完整目录结构，/health 接口
- 任务1.1.2 ✅：Vite + React 19 + TypeScript + Tailwind 4 + Zustand 5，7个页面骨架
- 任务1.1.3 ✅：Docker Compose 4服务编排（postgres + redis + api + frontend），代理 7897 通
- 任务1.1.4 ✅：Visitor/Conversation/Message/Agent/Staff/Workflow 模型，Alembic 迁移已应用
- 任务1.1.5 ✅：GET /health → {"status":"ok"}
- 任务1.1.6 ✅：Makefile 16个命令全部可执行
- 任务1.1.7 ✅：make check（ruff + mypy 29文件 + pytest + check-arch.sh 7项）全通过

### 遗留问题

- **Docker Hub 需代理**：`make dev` 必须在 `export http_proxy=http://127.0.0.1:7897` 环境下运行，否则无法拉取镜像。无代理时用 `make dev-local`。

### 下一步行动

1. 开始 Sprint 1.2：AI 对话核心
2. 第一个任务1.2.1：Claude SDK 集成，单元测试 Mock 通过 — 验证命令：`cd backend && pytest tests/unit/test_ai/ -v`

---

## 决策记录

| 日期 | 决策 | 原因 |
|------|------|------|
| 2025-07-24 | 单体架构，不拆微服务 | 团队1人，日咨询<50，过度设计无意义 |
| 2025-07-24 | Claude Sonnet 4 作为主模型 | 工具调用稳定，中文好，性价比高 |
| 2025-07-24 | pgvector 不另外部署向量库 | 少一个服务，运维简单 |
| 2025-07-24 | 企业微信而非公众号 | 客户要求企业微信沟通 |
