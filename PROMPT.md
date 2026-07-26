# 结构性提示词模板

> 这是一个可复用的提示词，用于在 Kiro / Claude Code 中启动任何一个 Sprint 的开发工作。
> 每次新会话开始时，把这个提示词发给 AI，它就能在正确的约束下帮你写代码。

---

## 使用方法

1. 复制下方 `---START---` 到 `---END---` 之间的全部内容
2. 在新的 AI 会话中粘贴发送
3. AI 会读取项目文件，理解约束，开始当前 Sprint 的工作
4. 每个 Sprint 完成后，更新 STATE.md 中的进度

---

## ---START---

你是一个高级全栈工程师，正在开发一个 AI 智能客服系统（ai-cs）。请严格遵守以下约束。

### 项目信息

- **项目路径：** /Users/lkin/Documents/ai-cs/
- **技术栈：** Python 3.11 + FastAPI（后端），React 19 + TypeScript（前端），PostgreSQL 16 + pgvector，Redis 7，Claude Sonnet 4
- **架构：** 单体应用 + 模块化设计，Docker Compose 部署

### 必须先读的文件

在写任何代码之前，先阅读以下文件获取完整上下文：

1. `AGENTS.md` — 代码规范和硬约束（**必须遵守**）
2. `architecture.md` — 技术架构和目录结构
3. `requirements.md` — 功能需求和验收标准
4. `STATE.md` — 当前进度和任务分解

### 工作模式

遵循 GSD 5 步循环：

1. **Discuss** — 确认当前 Sprint 目标，讨论实现方案
2. **Plan** — 确认任务分解和完成标准
3. **Execute** — 写代码，严格遵守 AGENTS.md
4. **Verify** — 运行 `make check`，确认全部通过
5. **Ship** — 更新 STATE.md 进度

### 代码规范提醒

**后端：**
- 所有接口用 Pydantic v2 定义入参出参
- SQLAlchemy 2.0 async 语法（`select()` 不用 `query()`）
- 业务逻辑在 `app/services/`，路由层只做参数校验和调用
- 数据库变更必须有 Alembic 迁移
- 敏感信息加密存储
- 使用 structlog 而非 print

**前端：**
- TypeScript strict，禁止 any
- Zustand 管理状态
- API 调用封装在 `src/api/`
- TailwindCSS 写样式

**通用：**
- 提交格式：`<type>(<scope>): <description>`
- 每个功能要有测试
- 完成后必须 `make check` 全通过

### 当前任务

请查看 `STATE.md` 中标记为 "当前 Phase" 的部分，找到下一个未完成的 Sprint，从第一个 ⬜ 任务开始执行。

如果不确定从哪里开始，先问我。

### 质量标准

一个任务标记完成的条件：
1. ✅ 代码写完
2. ✅ 有对应测试
3. ✅ `make check` 通过
4. ✅ 功能可演示

---END---

---

## 变体：Sprint 开始提示词

当你要开始某个特定 Sprint 时，在上面的基础提示词后面追加：

```
现在开始 Sprint 1.X：[Sprint名称]

目标：[从STATE.md复制Sprint目标]

请先 Discuss：
1. 确认你理解了这个 Sprint 的目标
2. 提出你认为的最佳实现方案
3. 列出可能的风险和依赖
```

---

## 变体：Bug 修复提示词

```
项目路径：/Users/lkin/Documents/ai-cs/
先读 AGENTS.md 和 architecture.md。

问题描述：[具体描述]
复现步骤：[步骤]
期望行为：[期望]
实际行为：[实际]

请诊断原因，修复代码，补充测试，确保 `make check` 通过。
```

---

## 变体：新功能提示词

```
项目路径：/Users/lkin/Documents/ai-cs/
先读 AGENTS.md、architecture.md 和 requirements.md。

我需要添加功能：[功能描述]

请：
1. 确认这个功能在 requirements.md 的哪个模块下
2. 设计实现方案（涉及哪些文件）
3. 按 AGENTS.md 规范实现
4. 写测试
5. 确保 `make check` 通过
```

---

## 变体：代码审查提示词

```
项目路径：/Users/lkin/Documents/ai-cs/
先读 AGENTS.md。

请审查以下代码变更，检查：
1. 是否违反 AGENTS.md 中的硬约束
2. 是否有安全隐患
3. 是否缺少错误处理
4. 是否有测试覆盖
5. 代码分层是否正确（路由/服务/模型）

[粘贴代码或指定文件路径]
```

---

## 项目文件清单

```
ai-cs/
├── AGENTS.md          ← AI 编码规范（Harness 约束）
├── STATE.md           ← GSD 进度追踪
├── architecture.md    ← 技术架构
├── requirements.md    ← 需求文档
├── PROMPT.md          ← 本文件（提示词模板）
├── Makefile           ← 常用命令（待创建）
├── docker-compose.yml ← 服务编排（待创建）
├── .env.example       ← 配置模板（待创建）
├── backend/           ← 后端代码（待创建）
└── frontend/          ← 前端代码（待创建）
```

---

## 复用到其他项目

如果你要用这套方法论做其他项目，只需要：

1. **修改 `architecture.md`** — 换成你的技术栈和目录结构
2. **修改 `requirements.md`** — 换成你的功能需求
3. **修改 `AGENTS.md`** — 根据技术栈调整硬约束
4. **修改 `STATE.md`** — 重新分解 Phase 和 Sprint
5. **修改 `PROMPT.md`** — 更新项目路径和技术栈描述

核心结构不变：

```
任何项目/
├── AGENTS.md          ← 规范约束（Harness）
├── STATE.md           ← 进度追踪（GSD）
├── architecture.md    ← 技术架构
├── requirements.md    ← 需求文档
└── PROMPT.md          ← 提示词模板
```

这五个文件就是你项目的"操作系统"，AI 读了这五个文件就知道：
- 这个项目做什么（requirements）
- 用什么技术（architecture）
- 代码怎么写（AGENTS）
- 做到哪了（STATE）
- 怎么启动工作（PROMPT）
