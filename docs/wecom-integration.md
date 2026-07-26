# 企业微信集成规范

> 修改 `app/integrations/wecom/`、`app/services/wecom_service.py`、`app/api/v1/internal/` 时必读。

---

## 代码位置

```
app/integrations/wecom/
├── client.py       # 企业微信 API 客户端（发消息、获取用户信息）
├── callback.py     # 回调消息的解析和路由
└── crypto.py       # 消息加解密（AES + SHA1 签名验证）

app/api/v1/internal/
└── wecom.py        # 回调路由：GET（URL 验证）/ POST（接收消息）

app/services/
└── wecom_service.py  # 企业微信业务逻辑（去重、路由、回复）
```

---

## 回调流程

```
企业微信服务器
    │
    ├─ GET /api/internal/wecom/callback?msg_signature=...&timestamp=...&nonce=...&echostr=...
    │       └─ 验证签名 → 解密 echostr → 原文返回
    │
    └─ POST /api/internal/wecom/callback?msg_signature=...&timestamp=...&nonce=...
            └─ 验证签名
            └─ AES 解密消息体
            └─ 解析 XML → 消息类型分发
            └─ 去重检查（MsgId）
            └─ 识别/创建 Visitor
            └─ 路由到 AI 或人工
            └─ 调 Claude → 生成回复
            └─ 调企业微信 API 发回消息
            └─ 返回 "success"（必须在 5 秒内返回）
```

**关键约束：** 企业微信要求回调接口在 **5 秒内** 响应 `"success"`，否则会重试。AI 生成回复时间超过 5 秒时，必须先异步处理：立即返回 `"success"`，在后台完成 AI 生成后再主动调用发消息 API。

---

## 签名验证

```python
# app/integrations/wecom/crypto.py
import hashlib

def verify_signature(
    token: str,
    timestamp: str,
    nonce: str,
    msg_signature: str,
    encrypt_msg: str = "",
) -> bool:
    """
    企业微信签名验证。
    签名 = SHA1(sort([token, timestamp, nonce, encrypt_msg]))
    """
    items = sorted([token, timestamp, nonce, encrypt_msg])
    signature = hashlib.sha1("".join(items).encode()).hexdigest()
    return hmac.compare_digest(signature, msg_signature)  # 防时序攻击
```

**规则：**
- 必须使用 `hmac.compare_digest` 比较签名，不用 `==`（防时序攻击）
- Token、EncodingAESKey、CorpID 从加密配置读取，不硬编码
- 签名验证失败时返回 403，记录日志，不抛出 500

---

## 消息解密

```python
# app/integrations/wecom/crypto.py
import base64
from Crypto.Cipher import AES

def decrypt_message(
    encoding_aes_key: str,
    encrypt_msg: str,
    corp_id: str,
) -> str:
    """AES-256-CBC 解密企业微信消息，返回 XML 字符串。"""
    key = base64.b64decode(encoding_aes_key + "=")
    cipher = AES.new(key, AES.MODE_CBC, key[:16])
    decrypted = cipher.decrypt(base64.b64decode(encrypt_msg))
    # 去掉随机字符串前缀（前 16 字节）和 PKCS7 填充
    content = decrypted[20:]
    xml_len = int.from_bytes(content[:4], "big")
    xml_content = content[4 : 4 + xml_len].decode("utf-8")
    # 验证 CorpID
    received_corp_id = content[4 + xml_len :].rstrip(b"\x00").decode()
    if received_corp_id != corp_id:
        raise ValueError("CorpID 不匹配")
    return xml_content
```

---

## 消息类型处理

```python
# app/integrations/wecom/callback.py
from enum import StrEnum

class MsgType(StrEnum):
    TEXT  = "text"
    IMAGE = "image"
    VOICE = "voice"
    EVENT = "event"

async def parse_message(xml_str: str) -> WeComMessage:
    """解析企业微信回调 XML，返回结构化消息。"""
    ...

# app/services/wecom_service.py
async def handle_message(msg: WeComMessage) -> None:
    # 1. 去重
    if await self._is_duplicate(msg.msg_id):
        return

    # 2. 识别访客
    visitor = await visitor_service.get_or_create_by_external_userid(
        msg.from_user_name
    )

    # 3. 路由
    if visitor.ai_disabled:
        await self._forward_to_staff(visitor, msg)
    else:
        await self._handle_with_ai(visitor, msg)

async def _is_duplicate(self, msg_id: str) -> bool:
    """Redis 去重，TTL 24 小时"""
    key = f"wecom:msg:{msg_id}"
    return not await redis.set(key, "1", nx=True, ex=86400)
```

**支持的消息类型：**

| 类型 | 处理方式 |
|------|----------|
| `text` | 直接传入 Claude |
| `image` | 下载图片 → base64 → Claude Vision |
| `voice` | 下载语音 → 转文字（可选）→ Claude |
| `event` | 关注/取关事件，更新 Visitor 状态 |

---

## 发送消息 API

```python
# app/integrations/wecom/client.py
class WeComClient:
    BASE_URL = "https://qyapi.weixin.qq.com/cgi-bin"

    async def get_access_token(self) -> str:
        """获取 access_token，Redis 缓存，自动续期。"""
        cached = await redis.get("wecom:access_token")
        if cached:
            return cached.decode()
        resp = await self.http.get(
            f"{self.BASE_URL}/gettoken",
            params={"corpid": self.corp_id, "corpsecret": self.corp_secret},
            timeout=10.0,
        )
        data = resp.json()
        token = data["access_token"]
        await redis.setex("wecom:access_token", data["expires_in"] - 60, token)
        return token

    async def send_text(self, to_user: str, content: str) -> None:
        """发送文本消息。"""
        token = await self.get_access_token()
        payload = {
            "touser": to_user,
            "msgtype": "text",
            "agentid": self.agent_id,
            "text": {"content": content},
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self.BASE_URL}/message/send",
                params={"access_token": token},
                json=payload,
            )
        data = resp.json()
        if data.get("errcode") != 0:
            raise ExternalServiceError(
                error_code="WECOM_SEND_FAILED",
                message=f"企业微信发送失败: {data.get('errmsg')}",
            )
```

**规则：**
- `access_token` 必须缓存在 Redis，不能每次请求都重新获取
- 所有 HTTP 请求设置 `timeout=10.0`
- 捕获 `httpx.TimeoutException`，转为 `ExternalServiceError`
- 发送失败时记录日志，不抛出到用户侧（回调接口要保证返回 `"success"`）

---

## 异步消息处理架构

由于 5 秒限制，AI 回复走异步流程：

```
POST /callback 收到消息
    │
    ├─ 去重 + 解析（同步，< 100ms）
    ├─ 返回 "success" 给企业微信
    │
    └─ 异步任务（Celery）
            ├─ 调用 Claude 生成回复（可能 2–5s）
            └─ 调 WeComClient.send_text() 发回给用户
```

```python
# app/api/v1/internal/wecom.py
@router.post("/callback")
async def receive_message(request: Request, background_tasks: BackgroundTasks):
    # 验证签名
    # 解密消息
    msg = await parse_message(decrypted_xml)

    # 立即返回，异步处理
    background_tasks.add_task(wecom_service.handle_message, msg)
    return PlainTextResponse("success")
```

---

## 环境变量

```bash
# .env（通过 security.py 加密存储到数据库，.env 只在初始化时使用）
WECOM_CORP_ID=your_corp_id
WECOM_AGENT_ID=your_agent_id
WECOM_CORP_SECRET=your_corp_secret      # 加密存库
WECOM_TOKEN=your_callback_token         # 加密存库
WECOM_ENCODING_AES_KEY=your_aes_key     # 加密存库
```

**安全规则：**
- `CORP_SECRET`、`TOKEN`、`ENCODING_AES_KEY` 在数据库中加密存储
- 使用 `app/core/security.py` 的 `encrypt_str()` / `decrypt_str()`
- 生产环境的 `.env` 不进 Git

---

## 测试规范

```python
# tests/integration/test_wecom/test_callback.py

# URL 验证测试（GET）
async def test_verify_url_valid_signature(client, mock_wecom_crypto):
    """签名正确时返回解密后的 echostr"""
    resp = await client.get(
        "/api/internal/wecom/callback",
        params={
            "msg_signature": "valid_sig",
            "timestamp": "1234567890",
            "nonce": "random",
            "echostr": "encrypted_echostr",
        }
    )
    assert resp.status_code == 200
    assert resp.text == "decrypted_echostr"

# 消息接收测试（POST）
async def test_receive_text_message(client, mock_wecom_crypto, mock_claude):
    """收到文本消息后异步处理，立即返回 success"""
    resp = await client.post(
        "/api/internal/wecom/callback",
        content=SAMPLE_ENCRYPTED_XML,
        params={"msg_signature": "...", "timestamp": "...", "nonce": "..."},
    )
    assert resp.status_code == 200
    assert resp.text == "success"

# 去重测试
async def test_dedup_same_msg_id(wecom_service, redis):
    """同一 MsgId 第二次调用直接返回，不处理"""
    await wecom_service.handle_message(sample_msg)
    await wecom_service.handle_message(sample_msg)  # 重复
    # 验证 Claude 只被调用一次
    assert mock_claude.call_count == 1
```

**Mock 策略：**
- 企业微信 API（发消息、获取 token）：必须 Mock
- AES 加解密：可以用真实实现（纯计算，无副作用）
- Redis：集成测试用真实 Redis（Docker）
