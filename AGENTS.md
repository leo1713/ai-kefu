# AGENTS.md — AI 编码约束规范

## 项目概览

Python 3.11 + FastAPI 后端，React 19 + TypeScript 前端，PostgreSQL 16 + pgvector 数据库。
单体应用，模块化设计。面向小微电商的 AI 智能客服系统。

---

## 快速命令

| 命令 | 作用 |
|------|------|
| `bash init.sh` | **会话启动检查**（每次新会话必须先跑） |
| `make setup` | 安装所有依赖，初始化数据库 |
| `make dev` | 启动开发环境（Docker Compose） |
| `make test` | 运行全部测试 |
| `make lint` | 代码规范检查（ruff + mypy + eslint） |
| `make check` | 完整验证（lint + test + build） |
| `make migrate` | 运行数据库迁移 |
| `make down` | 停止所有服务 |

---

## 硬约束（不可违反）

### 后端（Python）

1. **所有 API 入参和出参必须用 Pydantic v2 模型定义。** 禁止裸 dict 或 Any 类型出现在接口层。

2. **所有数据库查询必须用 SQLAlchemy 2.0 async 语法。** 使用 `select()` 语句，不使用 1.x 的 `db.query()` 风格。

3. **业务逻辑放 `app/services/`，不放在路由层。** 路由函数只做：参数校验 → 调 service → 返回结果。

4. **数据库模型变更必须同时提交 Alembic 迁移文件。** 运行 `alembic revision --autogenerate -m "描述"` 生成迁移。

5. **敏感信息（API Key、密码）加密存储。** 使用 `app/core/security.py` 中的 `encrypt_str()` / `decrypt_str()`。绝不明文存库。

6. **不使用 print()，使用 structlog 日志。** `from app.core.logging import logger`

7. **所有外部 HTTP 调用必须设置超时和错误处理。** 使用 httpx，设置 `timeout=10.0`，捕获 `httpx.TimeoutException`。

8. **异步函数使用 `async def`，不混用同步阻塞调用。** 如果必须调同步库，用 `asyncio.to_thread()` 包装。

### 前端（TypeScript）

1. **所有组件使用函数组件 + TypeScript strict 模式。** 禁止 `any` 类型，禁止 `// @ts-ignore`。

2. **状态管理使用 Zustand，不使用 Context 传递业务状态。**

3. **API 调用统一使用 `src/api/` 目录下的封装函数。** 不在组件里直接写 fetch。

4. **样式使用 TailwindCSS，不写自定义 CSS 文件。** 除非 Tailwind 无法实现的动画。

### 通用

1. **每个 PR 必须通过以下检查才能合并：**
   - `ruff check .`（Python 代码规范）
   - `mypy --strict app/`（Python 类型检查）
   - `pytest`（测试通过）
   - `tsc --noEmit`（TypeScript 编译检查）
   - `eslint .`（前端代码规范）

2. **提交信息格式：** `<type>(<scope>): <description>`
   - type: feat / fix / refactor / docs / test / chore
   - scope: api / ai / rag / wecom / frontend / db / deploy
   - 示例: `feat(ai): 实现 Agent 工具调用循环`

3. **文件命名：** Python 用 snake_case，TypeScript 用 PascalCase（组件）或 camelCase（工具函数）。

---

## 代码分层规范

```
请求进入
    ↓
app/api/v1/xxx.py        ← 路由层：参数校验，调 service，返回响应
    ↓
app/services/xxx.py      ← 业务层：核心逻辑，编排调用
    ↓
app/models/xxx.py        ← 数据层：SQLAlchemy 模型定义
app/schemas/xxx.py       ← 数据传输：Pydantic 请求/响应 Schema
```

**规则：**
- 路由层不直接操作数据库
- Service 层不直接返回 HTTP 响应
- Model 层不包含业务逻辑
- Schema 层不依赖 Model 层（可以从 Model 转换，但不 import Model）

---

## AI 模块规范

### Agent 配置结构

```python
# 每个 Agent 必须包含以下配置
AgentConfig(
    name="售后客服",
    system_prompt="你是...",      # 系统提示词
    model="claude-sonnet-4-20250514",  # 模型
    temperature=0.3,              # 温度
    max_tokens=2000,              # 最大输出
    tools=[...],                  # 绑定的工具列表
    knowledge_ids=[...],          # 绑定的知识库 ID
    workflow_id=None,             # 绑定的工作流（可选）
)
```

### 工具定义规范

```python
# 所有工具必须遵循此结构
class Tool:
    name: str                    # 唯一标识，snake_case
    description: str             # 给 AI 看的描述（决定何时调用）
    parameters: dict             # JSON Schema 格式的参数定义
    
    async def execute(self, **kwargs) -> str:
        """执行逻辑，返回字符串结果"""
        ...
```

### 流式响应规范

```python
# SSE 事件类型（前端必须处理这些）
"chat.started"          # 对话开始
"chat.content_chunk"    # 内容片段（流式文字）
"chat.tool_call"        # 工具调用开始
"chat.tool_result"      # 工具调用结果
"chat.completed"        # 对话完成
"chat.error"            # 错误
```

---

## 数据库规范

### 表命名

- 表名：`snake_case` 复数形式（`visitors`、`conversations`、`messages`）
- 外键：`<关联表单数>_id`（`visitor_id`、`agent_id`）
- 索引：`ix_<表名>_<字段>`
- 唯一约束：`uk_<表名>_<字段>`

### 必备字段

每张表必须包含：

```python
id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
created_at: Mapped[datetime] = mapped_column(default=func.now())
updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
```

### 软删除

需要删除功能的表使用软删除：

```python
deleted_at: Mapped[datetime | None] = mapped_column(default=None)
```

查询时默认过滤 `deleted_at IS NULL`。

---

## 测试规范

### 文件组织

```
tests/
├── unit/                  # 单元测试（不依赖外部服务）
│   ├── test_services/
│   └── test_ai/
├── integration/           # 集成测试（需要数据库）
│   ├── test_api/
│   └── test_wecom/
├── conftest.py           # 共享 fixtures
└── factories.py          # 测试数据工厂
```

### 测试命名

```python
# 函数名格式：test_<被测方法>_<场景>_<预期结果>
def test_create_visitor_new_user_returns_visitor():
    ...

def test_create_visitor_existing_user_returns_existing():
    ...

def test_chat_completion_ai_disabled_returns_error():
    ...
```

### Mock 策略

- 外部 API（Claude、企业微信、支付系统）：必须 Mock
- 数据库：集成测试用真实 PostgreSQL（Docker）
- Redis：集成测试用真实 Redis（Docker）

---

## 错误处理规范

### 统一异常类

```python
# app/core/exceptions.py
class AppException(Exception):
    status_code: int
    error_code: str
    message: str

class NotFoundError(AppException):       # 404
class ValidationError(AppException):     # 422
class AuthenticationError(AppException):  # 401
class PermissionError(AppException):     # 403
class ExternalServiceError(AppException): # 502
```

### API 错误响应格式

```json
{
    "error": {
        "code": "VISITOR_NOT_FOUND",
        "message": "访客不存在",
        "details": {}
    }
}
```

---

## 专题文档（按需阅读）

| 文档 | 什么时候读 |
|------|------------|
| `architecture.md` | 理解整体架构、技术选型时 |
| `requirements.md` | 了解功能需求、验收标准时 |
| `docs/api-patterns.md` | 添加新 API 端点时 |
| `docs/ai-patterns.md` | 修改 AI 模块（Agent/Tool/RAG）时 |
| `docs/wecom-integration.md` | 修改企业微信集成时 |
| `docs/database-rules.md` | 新增/修改数据库表时 |
| `docs/testing-guide.md` | 编写测试时 |

---

## 会话启动（Fresh Session Test）

> 新会话开始时，先运行 `bash init.sh` 验证环境，再用以下5个问题确认上下文，然后动手写代码。

```bash
bash init.sh   # 环境健康检查，全部 ✓ 才继续
```

1. **这是什么系统？** → 读 `AGENTS.md` 项目概览
2. **代码怎么组织？** → 读 `architecture.md`
3. **怎么运行？** → `make dev`，确认命令存在
4. **怎么验证？** → `make check && bash scripts/check-arch.sh`
5. **现在做到哪了？** → 读 `STATE.md` 的"上次会话记录"区块，找"下一步行动"

如果以上5个问题都能回答，可以直接开始工作。如果有任何一个答不上来，先读对应文档，不要猜。

**目标：3分钟内恢复到可执行状态。**

---

## WIP 规则（Work-In-Progress 限制）

**同一时间只允许1个任务处于 active 状态。**

- 完成当前任务的三层验证后，才能开始下一个任务
- 发现其他问题：记录到 `STATE.md` 遗留问题，本任务完成后再处理
- 不在实现 A 功能时"顺手"重构 B 模块
- 不同时打开多个 feature 的修改

**判断依据：** 当前任务的验证命令（见 STATE.md）全部返回 exit 0，才算完成。

---

## 任务完成标准（三层验证）

一个任务标记为 ✅ 的唯一条件是**三层验证全部通过**，缺一不可：

### 层1：静态分析（最低要求）

```bash
make check              # ruff + mypy + pytest + tsc + eslint
bash scripts/check-arch.sh   # 架构约束无违规
```

### 层2：运行时验证（核心证据）

- 应用能正常启动（`make dev` 无报错）
- 对应任务的验证命令（见 STATE.md）执行返回 exit 0
- 新增接口用 curl 实际调通，不只是"代码看起来对"

### 层3：端到端验证（最终防线）

- 涉及跨组件交互的功能，必须走完整用户路径
- 每个 Sprint 的"完成标志"描述的场景必须人工或脚本验证一遍
- "代码写完了"≠完成，"端到端跑通了"才算完成

> **错误示例：** 单元测试全绿 → 宣布完成 ✗  
> **正确示例：** 单元测试全绿 + curl 调通接口 + 端到端场景验证 → 宣布完成 ✓

---

## 会话结束（清洁退出检查清单）

每次会话结束前，必须逐项确认，全部通过才算交班完成：

```
□ 1. make check 通过（ruff + mypy + pytest + tsc + eslint）
□ 2. 当前任务状态已更新（🔄 进行中 / 🚫 阻塞 / ✅ 已完成）
□ 3. STATE.md「上次会话记录」已更新（完成了什么 / 遗留问题 / 下一步行动）
□ 4. 阻塞项已在遗留问题中写明原因和解除条件
□ 5. 无调试代码残留（print() / console.log / # TODO / debugger）
□ 6. git commit 已提交，repo 处于可恢复的干净状态
```

> **不做清洁退出的代价：** 下个会话需要重新诊断项目状态，浪费 15-20 分钟，还可能在混乱的基础上引入更多问题。

---

## 验证脚本（verify.sh）

每次代码变更后必须运行：

```bash
#!/bin/bash
set -e

echo "=== Python Lint ==="
cd backend && ruff check .

echo "=== Python Type Check ==="
mypy --strict app/

echo "=== Python Tests ==="
pytest --tb=short

echo "=== Frontend Type Check ==="
cd ../frontend/admin && tsc --noEmit

echo "=== Frontend Lint ==="
eslint .

echo "=== Architecture Constraints ==="
cd ../.. && bash scripts/check-arch.sh

echo "=== All Passed ✓ ==="
```

全部通过才能声称"功能完成"。

---

## Sprint 合约

每个 Sprint 开始前必须填写 Sprint 合约，确认范围、边界和完成标准。

模板位置：`docs/sprint-contract-template.md`

合约确认后本 Sprint 不新增范围。
