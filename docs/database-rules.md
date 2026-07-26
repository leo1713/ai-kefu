# 数据库操作约束

> 新增或修改数据库表、查询、迁移时必读。

---

## 硬约束（不可违反）

1. **所有查询使用 SQLAlchemy 2.0 async 语法**，禁止 `db.query()` 风格
2. **模型变更必须同时提交 Alembic 迁移文件**，不允许只改模型不迁移
3. **禁止在路由层直接操作数据库**，必须通过 service 层
4. **软删除优先**：有用户可见删除需求的表使用 `deleted_at`，不物理删除
5. **查询时默认过滤软删除记录**：所有查询默认加 `WHERE deleted_at IS NULL`

---

## 模型基类

所有模型必须继承 `Base` 并包含必备字段：

```python
# app/models/base.py
import uuid
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

class SoftDeleteMixin(TimestampMixin):
    """需要软删除的表额外继承此 Mixin"""
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)
```

```python
# 使用示例
class Visitor(Base, SoftDeleteMixin):
    __tablename__ = "visitors"

    external_userid: Mapped[str] = mapped_column(unique=True, index=True)
    nickname: Mapped[str | None]
    ai_disabled: Mapped[bool] = mapped_column(default=False)
```

---

## 命名规范

| 对象 | 格式 | 示例 |
|------|------|------|
| 表名 | `snake_case` 复数 | `visitors`、`knowledge_chunks` |
| 外键列 | `<关联表单数>_id` | `visitor_id`、`agent_id` |
| 普通索引 | `ix_<表名>_<字段>` | `ix_messages_conversation_id` |
| 唯一约束 | `uk_<表名>_<字段>` | `uk_visitors_external_userid` |
| 联合索引 | `ix_<表名>_<字段1>_<字段2>` | `ix_messages_conversation_id_created_at` |

---

## 查询规范

### 标准 CRUD 模式

```python
# app/services/visitor_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

class VisitorService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # 查询单条（软删除过滤）
    async def get(self, visitor_id: uuid.UUID) -> Visitor | None:
        stmt = (
            select(Visitor)
            .where(Visitor.id == visitor_id)
            .where(Visitor.deleted_at.is_(None))   # 必须
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # 查询列表（分页）
    async def list(
        self, limit: int = 20, offset: int = 0
    ) -> list[Visitor]:
        stmt = (
            select(Visitor)
            .where(Visitor.deleted_at.is_(None))
            .order_by(Visitor.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars())

    # 创建
    async def create(self, data: VisitorCreate) -> Visitor:
        visitor = Visitor(**data.model_dump())
        self.db.add(visitor)
        await self.db.flush()   # flush 获取 id，不 commit
        return visitor

    # 软删除
    async def delete(self, visitor_id: uuid.UUID) -> None:
        visitor = await self.get(visitor_id)
        if visitor:
            visitor.deleted_at = datetime.utcnow()
            await self.db.flush()
```

**规则：**
- 用 `flush()` 而不是 `commit()`，由路由层统一 commit（通过依赖注入的事务管理）
- 永远不直接 `db.commit()` 在 service 层，事务边界在路由层
- 列表查询必须有 `limit`，默认不超过 100 条

### 禁止写法

```python
# ❌ 1.x 风格
users = db.query(User).filter(User.id == uid).first()

# ❌ 不过滤软删除
stmt = select(Visitor).where(Visitor.id == visitor_id)

# ❌ service 层 commit
await self.db.commit()

# ❌ 无限制查询
stmt = select(Message)  # 可能返回几十万条
```

---

## 向量查询规范（pgvector）

```python
# app/models/knowledge.py
from pgvector.sqlalchemy import Vector

class KnowledgeChunk(Base, TimestampMixin):
    __tablename__ = "knowledge_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_documents.id"), index=True
    )
    content: Mapped[str]
    embedding: Mapped[list[float]] = mapped_column(Vector(1536))  # text-embedding-3-small 维度
    chunk_index: Mapped[int]

    __table_args__ = (
        # IVFFlat 索引，适合 < 100 万向量
        Index("ix_knowledge_chunks_embedding", "embedding",
              postgresql_using="ivfflat",
              postgresql_with={"lists": 100},
              postgresql_ops={"embedding": "vector_cosine_ops"}),
    )
```

```python
# 向量相似度查询
async def search(
    self,
    query_embedding: list[float],
    knowledge_ids: list[uuid.UUID],
    top_k: int = 5,
    score_threshold: float = 0.7,
) -> list[KnowledgeChunk]:
    stmt = (
        select(
            KnowledgeChunk,
            (1 - KnowledgeChunk.embedding.cosine_distance(query_embedding)).label("score"),
        )
        .where(KnowledgeChunk.document_id.in_(
            select(KnowledgeDocument.id).where(
                KnowledgeDocument.collection_id.in_(knowledge_ids),
                KnowledgeDocument.deleted_at.is_(None),
            )
        ))
        .where(KnowledgeChunk.deleted_at.is_(None))
        .order_by(text("score DESC"))
        .limit(top_k)
    )
    result = await self.db.execute(stmt)
    rows = result.all()
    return [row.KnowledgeChunk for row in rows if row.score >= score_threshold]
```

---

## 迁移流程

```bash
# 1. 修改 app/models/ 中的模型
# 2. 生成迁移文件（必须检查生成内容是否符合预期）
cd backend
alembic revision --autogenerate -m "add knowledge_chunks table"

# 3. 检查生成的迁移文件 alembic/versions/xxx.py
#    重点检查：是否有意外的 drop table / drop column

# 4. 应用迁移
alembic upgrade head

# 5. 验证
python -c "from app.models import KnowledgeChunk; print('OK')"
```

**迁移文件规则：**
- commit 时迁移文件和模型变更必须在同一个 commit
- 迁移描述用中文，清楚说明变更内容：`add_knowledge_chunks_table`
- 不允许在迁移文件里写业务逻辑
- 生产环境迁移前必须在测试环境验证通过

---

## 数据库连接规范

```python
# app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

engine = create_async_engine(
    settings.database_url,          # postgresql+asyncpg://...
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,             # 自动检测断开的连接
    echo=settings.debug,            # 仅 debug 模式打印 SQL
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,         # 避免 commit 后访问属性触发新查询
)

# 依赖注入
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        async with session.begin():   # 自动 commit/rollback
            yield session
```

---

## 常用表结构速查

```
visitors          — 访客（external_userid, nickname, ai_disabled）
conversations     — 会话（visitor_id, agent_id, status, staff_id）
messages          — 消息（conversation_id, role, content, msg_type）
agents            — Agent 配置（name, system_prompt, model, config_json）
knowledge_collections  — 知识库集合（name, description）
knowledge_documents    — 文档（collection_id, filename, status）
knowledge_chunks       — 分片 + 向量（document_id, content, embedding）
staff             — 客服（name, email, status）
system_configs    — 系统配置（key, encrypted_value）
```

详细字段定义见 `app/models/` 对应文件。
