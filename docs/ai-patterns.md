# AI 模块开发规范

> 修改 `app/ai/`、`app/services/chat_service.py`、`app/services/agent_service.py`、`app/services/rag_service.py` 时必读。

---

## 目录结构

```
app/ai/
├── agent_builder.py     # 根据 AgentConfig 构建运行时 Agent 实例
├── agent_runner.py      # 执行 Agent：加载上下文 → 调 Claude → 处理工具循环
├── tool_executor.py     # 分发并执行工具调用
├── rag_engine.py        # 向量检索：查询 pgvector，返回相关 chunk
├── streaming.py         # SSE 事件生成器，格式化流式输出
└── tools/               # 内置工具实现
    ├── order_query.py
    ├── refund_handler.py
    ├── payment_query.py
    ├── handoff.py
    └── user_info.py
```

---

## Agent 生命周期

每次对话调用路径：

```
chat_service.handle_message()
    │
    ├─ 1. 加载 AgentConfig（从数据库）
    ├─ 2. agent_builder.build() → AgentRuntime
    ├─ 3. rag_engine.retrieve() → 相关知识库 chunks
    ├─ 4. agent_runner.run()
    │       ├─ 组装 system prompt（原始 + RAG 上下文）
    │       ├─ 加载最近 N 轮历史消息
    │       ├─ 调用 Claude API（流式）
    │       └─ 工具调用循环（直到无工具调用或达到最大轮次）
    └─ 5. streaming.emit_events() → SSE 响应
```

---

## AgentConfig 规范

```python
# app/schemas/agent.py
class AgentConfig(BaseModel):
    name: str
    system_prompt: str
    model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.3          # 范围 0.0 – 1.0
    max_tokens: int = 2000            # 最大输出 token 数
    tools: list[str] = []             # 工具 name 列表，对应 tools/ 目录
    knowledge_ids: list[uuid.UUID] = []  # 绑定的知识库集合 ID
    workflow_id: uuid.UUID | None = None
```

**约束：**
- `temperature` 客服场景用 0.1–0.4，创意生成用 0.7–1.0
- `max_tokens` 不超过 4096（成本控制）
- `tools` 列表中的名称必须与 `app/ai/tools/` 下的文件名一致

---

## 工具定义规范

每个工具必须继承 `BaseTool` 并实现 `execute()`：

```python
# app/ai/tools/base.py
from abc import ABC, abstractmethod
from pydantic import BaseModel

class BaseTool(ABC):
    name: str                 # snake_case，唯一标识
    description: str          # 给 Claude 看的描述，决定何时调用，要精确
    parameters: dict          # JSON Schema 格式

    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """返回字符串。Claude 将原文读取此结果。"""
        ...
```

**工具编写规则：**
1. `description` 必须说清楚"什么情况下调用"，不只说"能做什么"
2. `execute()` 必须返回 `str`，不返回 dict 或模型对象
3. 工具内部调用外部 HTTP 必须设置 `timeout=10.0`，捕获 `httpx.TimeoutException`
4. 工具执行失败返回描述性错误字符串，不抛出异常（Claude 会据此生成友好回复）
5. 工具不直接操作数据库，通过 service 层访问

```python
# 正确示例
async def execute(self, order_id: str) -> str:
    try:
        order = await order_service.get(order_id)
        if not order:
            return f"未找到订单 {order_id}"
        return f"订单状态：{order.status}，下单时间：{order.created_at}"
    except httpx.TimeoutException:
        return "查询超时，请稍后重试"
    except Exception as e:
        logger.error("order_query failed", order_id=order_id, error=str(e))
        return "查询失败，请联系客服"
```

---

## RAG 检索规范

```python
# app/ai/rag_engine.py
async def retrieve(
    query: str,
    knowledge_ids: list[uuid.UUID],
    top_k: int = 5,
    score_threshold: float = 0.7,
) -> list[KnowledgeChunk]:
    """
    返回相关度高于阈值的 top_k 个 chunk。
    score_threshold 低于此值的结果不注入 prompt。
    """
```

**RAG 注入规则：**
- 检索到相关 chunk 时，将其作为 `<context>` 块放在 system prompt 末尾
- 未检索到相关内容（空结果或全低于阈值）时，**不注入任何内容**，让 Claude 用通用知识回答
- 注入格式固定，不在 system prompt 里拼接自由文本

```python
RAG_CONTEXT_TEMPLATE = """
<context>
以下是从知识库检索到的相关内容，请优先基于此回答：

{chunks}
</context>
"""
```

- 单次注入的 chunk 总 token 数不超过 2000（防止挤占对话历史预算）

---

## 流式响应规范

SSE 事件类型和格式，前端必须处理全部类型：

```python
# 事件类型常量（app/ai/streaming.py）
EVENT_CHAT_STARTED    = "chat.started"
EVENT_CONTENT_CHUNK   = "chat.content_chunk"
EVENT_TOOL_CALL       = "chat.tool_call"
EVENT_TOOL_RESULT     = "chat.tool_result"
EVENT_COMPLETED       = "chat.completed"
EVENT_ERROR           = "chat.error"
```

```jsonc
// chat.started
{"event": "chat.started", "data": {"conversation_id": "uuid"}}

// chat.content_chunk（逐字流式）
{"event": "chat.content_chunk", "data": {"delta": "你好"}}

// chat.tool_call（工具调用开始）
{"event": "chat.tool_call", "data": {"tool": "order_query", "input": {"order_id": "123"}}}

// chat.tool_result（工具调用完成）
{"event": "chat.tool_result", "data": {"tool": "order_query", "output": "订单状态：已发货"}}

// chat.completed
{"event": "chat.completed", "data": {"message_id": "uuid", "usage": {"input_tokens": 100, "output_tokens": 50}}}

// chat.error
{"event": "chat.error", "data": {"code": "API_TIMEOUT", "message": "AI 服务响应超时，请重试"}}
```

**规则：**
- 每个对话必须发送 `chat.started` 开头和 `chat.completed` / `chat.error` 结尾
- 工具调用必须先发 `chat.tool_call`，完成后发 `chat.tool_result`，再继续 `content_chunk`
- 错误时发 `chat.error` 并中止流，不发 `chat.completed`

---

## Claude API 调用规范

```python
# app/ai/agent_runner.py
import anthropic

client = anthropic.AsyncAnthropic(
    api_key=settings.anthropic_api_key,  # 从加密配置读取，不硬编码
)

# 流式调用
async with client.messages.stream(
    model=agent_config.model,
    max_tokens=agent_config.max_tokens,
    temperature=agent_config.temperature,
    system=system_prompt,
    messages=history,
    tools=tool_schemas,
) as stream:
    async for event in stream:
        ...
```

**约束：**
- API Key 通过 `settings.anthropic_api_key` 读取，由 `app/core/security.py` 解密
- 捕获 `anthropic.APITimeoutError`、`anthropic.APIConnectionError`、`anthropic.RateLimitError`
- 工具调用循环最大轮次：10 轮（防止死循环）
- 对话历史最多保留最近 10 轮（20 条消息），超出时截断最老的轮次

---

## 上下文窗口预算管理

| 预算项 | 上限 | 说明 |
|--------|------|------|
| system prompt | 1000 tokens | 包含角色定义 + 工具说明 |
| RAG 上下文 | 2000 tokens | 知识库 chunk 注入 |
| 对话历史 | 6000 tokens | 最近 10 轮 |
| 输出预留 | 2000 tokens | max_tokens |
| **总计** | **~11000 tokens** | 远低于模型限制，保留余量 |

---

## 测试规范（AI 模块专项）

```python
# 外部 API 必须 Mock，不发真实请求
@pytest.fixture
def mock_claude(monkeypatch):
    async def fake_stream(*args, **kwargs):
        yield anthropic.types.ContentBlockDeltaEvent(
            delta=anthropic.types.TextDelta(text="你好，有什么可以帮助您？"),
            ...
        )
    monkeypatch.setattr("anthropic.AsyncAnthropic.messages.stream", fake_stream)

# 工具测试：直接调用 execute()，Mock 外部依赖
async def test_order_query_not_found():
    tool = OrderQueryTool()
    result = await tool.execute(order_id="NONEXISTENT")
    assert "未找到" in result

# RAG 测试：Mock 向量搜索结果
async def test_rag_retrieval_above_threshold():
    engine = RAGEngine(db=mock_db)
    chunks = await engine.retrieve("退款政策", knowledge_ids=[...])
    assert all(c.score >= 0.7 for c in chunks)
```

---

## 常见错误和处理方式

| 错误场景 | 处理方式 | 用户侧表现 |
|----------|----------|------------|
| Claude API 超时 | 发 `chat.error`，error_code=`API_TIMEOUT` | "AI 服务响应超时，请重试" |
| Claude API 限流 | 等待 1s 后重试一次，仍失败则发错误 | "服务繁忙，请稍后重试" |
| 工具调用循环超过 10 轮 | 强制结束工具循环，生成最终回复 | 正常回复，工具结果可能不完整 |
| RAG 检索无结果 | 不注入上下文，继续正常对话 | AI 用通用知识回答 |
| 工具执行异常 | 工具返回错误字符串，Claude 据此生成回复 | "查询失败，请联系客服" |
