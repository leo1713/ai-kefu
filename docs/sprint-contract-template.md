# Sprint 合约模板

> 每个 Sprint 开始前填写此合约，AI 和人类双方对齐范围和完成标准。
> 合约一旦确认，本 Sprint 内不新增范围（变更走下一个 Sprint）。

---

## Sprint 合约：[Sprint 编号] — [Sprint 名称]

**日期：** YYYY-MM-DD  
**预计周期：** X 天  

---

### 一、本次做什么（范围）

> 列出本 Sprint 要完成的任务 ID（来自 STATE.md）

- [ ] [任务ID] [行为描述]
- [ ] [任务ID] [行为描述]
- [ ] [任务ID] [行为描述]

### 二、本次不做什么（边界）

> 明确排除，防止 AI 越权扩展

- 不修改 [模块/文件]（留给 Sprint X.X）
- 不实现 [功能]（超出本 Sprint 范围）
- 不重构现有代码（除非直接阻塞本任务）

### 三、完成标准（三层验证）

**层1 — 静态分析（必须）**
```bash
make check   # ruff + mypy + pytest + tsc + eslint 全通过
bash scripts/check-arch.sh   # 架构约束无违规
```

**层2 — 运行时验证（必须）**
> 列出本 Sprint 的具体运行时检查命令（从 STATE.md 任务的验证命令复制）

```bash
# 示例
curl -sf http://localhost:8000/health | python -c "import sys,json; assert json.load(sys.stdin)['status']=='ok'"
```

**层3 — 端到端验证（必须）**
> 描述一个完整的用户操作路径，证明功能真正可用

```
场景：[描述端到端场景]
步骤：
  1. [操作步骤]
  2. [操作步骤]
预期结果：[可观测的结果]
```

### 四、已知风险和依赖

| 风险/依赖 | 影响 | 应对方案 |
|----------|------|---------|
| [风险描述] | [影响范围] | [应对方法] |

### 五、WIP 规则（必读）

- 同一时间只有 **1个任务** 处于 active 状态
- 当前任务的三层验证全部通过后，才能开始下一个任务
- 不在完成当前任务的同时"顺手"修改其他模块
- 发现其他问题：记录到 STATE.md 遗留问题区，本 Sprint 不处理

---

## 填写示例：Sprint 1.2 合约

**日期：** 2025-08-05  
**预计周期：** 5 天  

### 一、本次做什么

- [ ] 1.2.1 Claude SDK 集成，单元测试 Mock 通过
- [ ] 1.2.2 Agent 模型和配置，seed 默认 Agent 写入数据库
- [ ] 1.2.3 `POST /api/v1/chat/completion` 返回流式回复
- [ ] 1.2.4 SSE 流式响应前端可逐字显示
- [ ] 1.2.5 消息历史写入数据库
- [ ] 1.2.6 连续对话能记住上下文（最近10轮）
- [ ] 1.2.7 API Key 无效/超时返回统一错误格式

### 二、本次不做什么

- 不接入知识库（RAG 留给 Sprint 1.3）
- 不实现企业微信回调（留给 Sprint 1.4）
- 不开发管理后台界面（留给 Sprint 1.5）
- 不优化 Claude 调用成本

### 三、完成标准

**层1 — 静态分析**
```bash
make check && bash scripts/check-arch.sh
```

**层2 — 运行时验证**
```bash
# 聊天接口返回流式回复
curl -sf -X POST http://localhost:8000/api/v1/chat/completion \
  -H "Content-Type: application/json" \
  -d '{"message":"你好","visitor_id":"test-001"}' \
  | grep "chat.completed"

# 数据库有消息记录
cd backend && python -c "
import asyncio
from app.database import get_db
from sqlalchemy import select
from app.models import Message
async def check():
    async for db in get_db():
        result = await db.execute(select(Message).limit(1))
        assert result.scalar_one_or_none() is not None, 'No messages in DB'
        print('OK: messages exist')
asyncio.run(check())
"
```

**层3 — 端到端验证**
```
场景：连续对话上下文记忆
步骤：
  1. POST /chat/completion {"message": "我叫小明"}
  2. POST /chat/completion {"message": "我叫什么名字？"} (同 conversation_id)
预期结果：第2条回复中包含"小明"
```

### 四、已知风险

| 风险 | 影响 | 应对 |
|------|------|------|
| Claude API 没有配置 Key | 所有 AI 调用失败 | 先用 Mock 完成单元测试，集成测试前配置真实 Key |
| SSE 在某些代理下被缓冲 | 流式显示失效 | 配置 Nginx 禁用缓冲：`proxy_buffering off` |
