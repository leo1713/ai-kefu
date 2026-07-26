# API 设计规范

## URL 规范

### 基本格式

```
/api/v1/<资源名复数>
/api/v1/<资源名复数>/<id>
/api/v1/<资源名复数>/<id>/<子资源>
```

### 示例

```
GET    /api/v1/visitors              ← 获取访客列表
POST   /api/v1/visitors              ← 创建访客
GET    /api/v1/visitors/{id}         ← 获取单个访客
PUT    /api/v1/visitors/{id}         ← 更新访客
DELETE /api/v1/visitors/{id}         ← 删除访客

GET    /api/v1/visitors/{id}/conversations  ← 获取访客的会话列表

POST   /api/v1/chat/completion       ← 发送聊天消息（动作型接口）
POST   /api/v1/knowledge/upload      ← 上传文档（动作型接口）
```

### 命名规则

| 规则 | 正确 | 错误 |
|------|------|------|
| 资源名用复数 | `/visitors` | `/visitor` |
| 用连字符分隔 | `/knowledge-bases` | `/knowledgeBases` |
| 全小写 | `/api/v1/agents` | `/API/V1/Agents` |
| 不用动词 | `POST /visitors` | `POST /create-visitor` |
| 动作型用名词 | `POST /chat/completion` | `POST /chat/send-message` |

---

## HTTP 方法语义

| 方法 | 语义 | 幂等 | 示例 |
|------|------|------|------|
| GET | 获取资源 | ✅ | 获取访客列表 |
| POST | 创建资源 / 执行操作 | ❌ | 创建访客、发送消息 |
| PUT | 全量更新 | ✅ | 更新访客全部信息 |
| PATCH | 部分更新 | ✅ | 只更新访客昵称 |
| DELETE | 删除资源 | ✅ | 删除知识库文档 |

---

## 请求格式

### 路径参数

```python
# 资源 ID
@router.get("/visitors/{visitor_id}")
async def get_visitor(visitor_id: uuid.UUID):
    ...
```

### 查询参数（列表筛选、分页）

```python
@router.get("/visitors")
async def list_visitors(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    search: str | None = Query(None),
):
    ...
```

### 请求体（创建/更新）

```python
class CreateAgentRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    system_prompt: str = Field(..., min_length=10, max_length=10000)
    model: str = Field(default="claude-sonnet-4-20250514")
    temperature: float = Field(default=0.3, ge=0, le=2)
    max_tokens: int = Field(default=2000, ge=100, le=8000)
    knowledge_ids: list[uuid.UUID] = Field(default_factory=list)
    tool_ids: list[str] = Field(default_factory=list)
```

---

## 响应格式

### 成功响应

**单个资源：**

```json
{
    "id": "uuid-xxx",
    "name": "售后客服",
    "created_at": "2025-07-24T10:00:00Z",
    "updated_at": "2025-07-24T10:00:00Z"
}
```

**列表资源（带分页）：**

```json
{
    "data": [
        { "id": "uuid-1", "name": "访客A" },
        { "id": "uuid-2", "name": "访客B" }
    ],
    "pagination": {
        "page": 1,
        "page_size": 20,
        "total": 156,
        "total_pages": 8
    }
}
```

**操作成功（无返回内容）：**

```
HTTP 204 No Content
```

### 错误响应

**统一格式：**

```json
{
    "error": {
        "code": "VISITOR_NOT_FOUND",
        "message": "访客不存在",
        "details": {
            "visitor_id": "uuid-xxx"
        }
    }
}
```

**错误码命名规则：** `<资源>_<动作/状态>`，全大写下划线分隔。

### HTTP 状态码使用

| 状态码 | 含义 | 什么时候用 |
|--------|------|------------|
| 200 | 成功 | GET/PUT/PATCH 成功 |
| 201 | 已创建 | POST 创建成功 |
| 204 | 无内容 | DELETE 成功 |
| 400 | 请求错误 | 业务逻辑拒绝（余额不足等） |
| 401 | 未认证 | 没有 Token 或 Token 过期 |
| 403 | 无权限 | Token 有效但没有权限 |
| 404 | 不存在 | 资源 ID 找不到 |
| 422 | 参数错误 | Pydantic 校验失败 |
| 429 | 限流 | 请求频率超限 |
| 500 | 服务器错误 | 未捕获的异常 |
| 502 | 外部服务错误 | Claude API / 企微 API 失败 |

---

## 分页规范

### 请求

```
GET /api/v1/visitors?page=1&page_size=20
```

| 参数 | 类型 | 默认值 | 范围 |
|------|------|--------|------|
| page | int | 1 | >= 1 |
| page_size | int | 20 | 1-100 |

### 响应

```python
class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int

class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    pagination: PaginationMeta
```

### 实现

```python
# app/core/pagination.py
from sqlalchemy import select, func

async def paginate(db, query, page: int, page_size: int):
    # 计算总数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()
    
    # 分页查询
    offset = (page - 1) * page_size
    items = (await db.execute(
        query.offset(offset).limit(page_size)
    )).scalars().all()
    
    return {
        "data": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
        }
    }
```

---

## 认证规范

### 需要认证的接口

所有 `/api/v1/` 下的接口默认需要 JWT 认证，除了：

```python
# 不需要认证的白名单
PUBLIC_PATHS = [
    "/health",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/internal/wecom/callback",  # 用签名验证代替
]
```

### 认证依赖注入

```python
# app/core/deps.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Staff:
    """验证 JWT Token，返回当前用户"""
    payload = verify_token(credentials.credentials)
    user = await staff_service.get_by_id(db, payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user

# 使用方式
@router.get("/visitors")
async def list_visitors(
    current_user: Staff = Depends(get_current_user),  # 自动验证
    db: AsyncSession = Depends(get_db),
):
    ...
```

---

## 版本控制

当前只有 v1，URL 前缀 `/api/v1/`。

如果将来需要 v2：
- v1 保持不动，继续服务
- v2 在 `/api/v2/` 下新建路由
- 两个版本共存一段时间
- 通知客户端迁移后废弃 v1

---

## SSE 流式接口规范

AI 聊天接口返回 SSE 流：

```
POST /api/v1/chat/completion
Content-Type: application/json
Accept: text/event-stream

响应：
Content-Type: text/event-stream

data: {"event": "chat.started", "data": {"conversation_id": "xxx"}}

data: {"event": "chat.content_chunk", "data": {"content": "你"}}

data: {"event": "chat.content_chunk", "data": {"content": "好"}}

data: {"event": "chat.tool_call", "data": {"tool": "query_order", "args": {"order_id": "123"}}}

data: {"event": "chat.tool_result", "data": {"tool": "query_order", "result": "已发货"}}

data: {"event": "chat.content_chunk", "data": {"content": "您的订单已发货"}}

data: {"event": "chat.completed", "data": {"usage": {"input_tokens": 150, "output_tokens": 80}}}

```

**前端处理：**

```typescript
const eventSource = new EventSource('/api/v1/chat/completion');
eventSource.onmessage = (event) => {
    const { event: type, data } = JSON.parse(event.data);
    switch (type) {
        case 'chat.content_chunk':
            appendMessage(data.content);
            break;
        case 'chat.completed':
            closeConnection();
            break;
    }
};
```

---

## 接口文档

FastAPI 自动生成 OpenAPI 文档：

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

**要求：**
- 每个路由函数必须有 docstring（会显示在文档里）
- 复杂接口加 `description` 和 `summary` 参数
- 响应模型用 `response_model` 标注

```python
@router.post(
    "/chat/completion",
    summary="发送聊天消息",
    description="向 AI 发送消息，返回 SSE 流式响应。需要有效的 visitor_id。",
    response_class=StreamingResponse,
)
async def chat_completion(req: ChatRequest):
    """
    处理访客聊天请求，返回 AI 流式回复。
    
    流程：验证访客 → 加载 Agent → RAG 检索 → 调用 Claude → 流式返回
    """
    ...
```
