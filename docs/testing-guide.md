# 测试规范

## 测试工具

| 工具 | 用途 |
|------|------|
| pytest | 测试框架 |
| pytest-asyncio | 异步测试支持 |
| httpx | 测试 FastAPI 接口（AsyncClient） |
| factory-boy | 生成测试数据 |
| pytest-cov | 覆盖率统计 |
| respx | Mock HTTP 请求（Claude API、企业微信等） |

---

## 目录结构

```
backend/tests/
├── conftest.py              # 共享 fixtures（数据库、客户端等）
├── factories.py             # 测试数据工厂（Factory Boy）
│
├── unit/                    # 单元测试（不依赖外部服务）
│   ├── test_services/       # 业务逻辑层测试
│   │   ├── test_chat_service.py
│   │   ├── test_visitor_service.py
│   │   └── test_rag_service.py
│   └── test_ai/            # AI 模块测试
│       ├── test_agent_builder.py
│       └── test_tool_executor.py
│
├── integration/             # 集成测试（需要真实数据库/Redis）
│   ├── test_api/            # API 接口测试
│   │   ├── test_chat_api.py
│   │   ├── test_knowledge_api.py
│   │   └── test_visitor_api.py
│   └── test_wecom/          # 企业微信集成测试
│       └── test_callback.py
│
└── fixtures/                # 测试用的静态文件
    ├── sample.pdf
    └── wecom_callback.xml
```

---

## 命名规范

### 测试文件

```
test_<被测模块>.py

示例：
test_chat_service.py      ← 测试 services/chat_service.py
test_chat_api.py          ← 测试 api/v1/chat.py
test_agent_builder.py     ← 测试 ai/agent_builder.py
```

### 测试函数

```python
# 格式：test_<被测方法>_<场景>_<预期结果>

# 正常场景
def test_create_visitor_new_user_returns_visitor():
    ...

# 边界场景
def test_create_visitor_duplicate_returns_existing():
    ...

# 错误场景
def test_create_visitor_invalid_data_raises_validation_error():
    ...

# 异步测试
async def test_chat_completion_returns_stream():
    ...
```

---

## 测试分类和策略

### 单元测试（unit/）

**特点：**
- 不依赖数据库、Redis、外部 API
- 所有外部依赖用 Mock
- 执行速度快（< 1秒/个）
- 测试纯业务逻辑

**什么时候写：** 每个 Service 层函数都要有单元测试。

```python
# 示例：测试聊天服务
import pytest
from unittest.mock import AsyncMock, patch
from app.services.chat_service import ChatService

@pytest.mark.asyncio
async def test_process_message_ai_enabled_calls_claude():
    """AI 开启时，消息应该发给 Claude 处理"""
    # Arrange（准备）
    mock_claude = AsyncMock(return_value="你好，有什么可以帮你？")
    service = ChatService(claude_client=mock_claude)
    
    # Act（执行）
    result = await service.process_message(
        visitor_id="v-123",
        message="你好"
    )
    
    # Assert（验证）
    assert result.reply == "你好，有什么可以帮你？"
    mock_claude.assert_called_once()


@pytest.mark.asyncio
async def test_process_message_ai_disabled_returns_none():
    """AI 禁用时，不调用 Claude，返回 None"""
    service = ChatService(claude_client=AsyncMock())
    service.is_ai_disabled = True
    
    result = await service.process_message(
        visitor_id="v-123",
        message="你好"
    )
    
    assert result is None
```

### 集成测试（integration/）

**特点：**
- 需要真实的 PostgreSQL 和 Redis（Docker 容器）
- 测试接口的完整链路（请求 → 处理 → 数据库 → 响应）
- 外部 API（Claude、企微）仍然 Mock
- 执行速度中等（1-5秒/个）

**什么时候写：** 每个 API 端点至少有正常和错误两个测试。

```python
# 示例：测试聊天 API
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_chat_completion_success(client: AsyncClient, mock_claude):
    """正常聊天请求返回 AI 回复"""
    response = await client.post("/api/v1/chat/completion", json={
        "message": "你们怎么退款？",
        "visitor_id": "v-123"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert data["conversation_id"] is not None


@pytest.mark.asyncio
async def test_chat_completion_empty_message_returns_422(client: AsyncClient):
    """空消息返回 422 参数错误"""
    response = await client.post("/api/v1/chat/completion", json={
        "message": "",
        "visitor_id": "v-123"
    })
    
    assert response.status_code == 422
```

---

## Mock 策略

### 必须 Mock 的（永远不真实调用）

| 外部服务 | Mock 方式 | 原因 |
|----------|-----------|------|
| Claude API | respx 或 unittest.mock | 花钱、慢、不稳定 |
| 企业微信 API | respx | 需要真实企业账号 |
| 支付系统 API | respx | 安全风险 |

### 使用真实服务的（Docker 容器）

| 服务 | 说明 |
|------|------|
| PostgreSQL | 集成测试用真实数据库，每个测试用事务回滚 |
| Redis | 集成测试用真实 Redis，每个测试前清空 |

### conftest.py 关键 fixtures

```python
# backend/tests/conftest.py
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app.main import app
from app.database import get_db

# 测试数据库（每次测试自动回滚）
@pytest.fixture
async def db_session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSession(engine) as session:
        yield session
        await session.rollback()

# 测试 HTTP 客户端
@pytest.fixture
async def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as c:
        yield c

# Mock Claude API
@pytest.fixture
def mock_claude():
    with patch("app.ai.agent_runner.claude_client") as mock:
        mock.messages.create = AsyncMock(return_value=MockResponse("你好"))
        yield mock
```

---

## 覆盖率要求

| 模块 | 最低覆盖率 | 说明 |
|------|-----------|------|
| app/services/ | 80% | 核心业务逻辑 |
| app/ai/ | 70% | AI 模块（部分依赖外部行为难测） |
| app/api/ | 60% | 路由层（主要靠集成测试） |
| app/models/ | 不要求 | 模型定义没有逻辑 |
| app/core/ | 50% | 基础设施 |

运行覆盖率：

```bash
pytest --cov=app --cov-report=term-missing
```

---

## 运行测试的命令

```bash
# 全部测试
make test

# 只跑单元测试（快）
pytest tests/unit/ -v

# 只跑集成测试
pytest tests/integration/ -v

# 跑特定文件
pytest tests/unit/test_services/test_chat_service.py -v

# 带覆盖率
pytest --cov=app --cov-report=html

# 只跑上次失败的
pytest --lf
```

---

## 什么时候写测试

**不是写完所有代码再补测试，而是：**

1. 写 Service 层函数 → 立刻写单元测试
2. 写 API 端点 → 立刻写集成测试
3. 修 Bug → 先写复现 Bug 的测试 → 再修代码 → 测试变绿

**每个 Sprint 的任务完成条件都包含"有对应测试"。**
