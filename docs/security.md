# 安全规范

## 安全原则

1. **最小权限：** 每个模块只能访问它需要的数据
2. **纵深防御：** 不依赖单一安全措施，多层保护
3. **默认安全：** 新功能默认拒绝，显式授权才放行
4. **密钥不落地：** 明文密钥只存在内存中，持久化必须加密

---

## 认证体系

### 管理后台：JWT Token

```
登录流程：
管理员 → POST /api/v1/auth/login (username + password)
       ← 200 { access_token, refresh_token, expires_in }

后续请求：
Header: Authorization: Bearer <access_token>
```

**JWT 配置：**

| 参数 | 值 | 说明 |
|------|-----|------|
| 算法 | HS256 | 对称加密，单服务够用 |
| access_token 有效期 | 2 小时 | 过期后用 refresh_token 刷新 |
| refresh_token 有效期 | 7 天 | 过期后需重新登录 |
| 密钥来源 | .env 的 JWT_SECRET_KEY | 至少 32 字符随机串 |

**代码实现：**

```python
# app/core/security.py
from datetime import datetime, timedelta
from jose import jwt, JWTError

def create_access_token(data: dict) -> str:
    expires = datetime.utcnow() + timedelta(hours=2)
    payload = {**data, "exp": expires, "type": "access"}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        raise AuthenticationError("Token 无效或已过期")
```

### 外部 API 调用：API Key

企业微信回调、网页聊天组件等外部调用使用 API Key：

```
Header: X-API-Key: <api_key>
```

API Key 在管理后台生成，加密存储在数据库中。

### 不需要认证的接口

| 接口 | 原因 |
|------|------|
| `GET /health` | 健康检查 |
| `POST /api/internal/wecom/callback` | 企业微信回调（用签名验证） |
| `POST /api/v1/auth/login` | 登录接口本身 |

---

## 密钥管理

### API Key 加密存储

```python
# app/core/crypto.py
import hashlib
import base64
from cryptography.fernet import Fernet

def _get_fernet() -> Fernet:
    """从 SECRET_KEY 派生 Fernet 密钥"""
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))

def encrypt_str(plaintext: str) -> str:
    """加密字符串，返回密文"""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()

def decrypt_str(ciphertext: str) -> str:
    """解密字符串，返回明文"""
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()

def mask_secret(plaintext: str) -> str:
    """脱敏显示，只保留后4位"""
    if len(plaintext) <= 4:
        return "****"
    return "*" * (len(plaintext) - 4) + plaintext[-4:]
```

### 密钥生命周期

```
管理员在后台填入 Claude API Key
    ↓
encrypt_str() 加密
    ↓
密文存入 PostgreSQL
    ↓
需要调用 Claude 时：decrypt_str() 在内存解密
    ↓
用完后变量出作用域，内存回收
    ↓
前端展示时：mask_secret() 脱敏显示 "sk-****abcd"
```

### .env 文件规则

```bash
# .env.example（提交到 Git，不含真实值）
SECRET_KEY=change-me-to-random-32-chars
JWT_SECRET_KEY=change-me-to-another-random-string
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/aics
REDIS_URL=redis://localhost:6379/0
CLAUDE_API_KEY=sk-ant-xxxxx
WECOM_CORP_ID=your-corp-id
WECOM_AGENT_ID=your-agent-id
WECOM_SECRET=your-secret
WECOM_TOKEN=your-callback-token
WECOM_ENCODING_AES_KEY=your-encoding-key
```

**绝对不提交的文件（.gitignore 中）：**

```
.env
.env.local
.env.production
```

---

## 企业微信回调安全

### 签名验证流程

```
企业微信发请求时带参数：
GET/POST ?msg_signature=xxx&timestamp=xxx&nonce=xxx

验证步骤：
1. 取出 timestamp + nonce + token（你配置的回调 Token）
2. 三者拼接后 SHA1 加密
3. 对比结果和 msg_signature
4. 一致 → 请求合法
5. 不一致 → 拒绝（返回 403）
```

### 消息加解密

```python
# 企业微信使用 AES-256-CBC 加密消息体
# 使用官方提供的 WXBizMsgCrypt 库

from app.integrations.wecom.crypto import WXBizMsgCrypt

def verify_callback(msg_signature, timestamp, nonce, echostr):
    """验证回调 URL（GET 请求）"""
    crypt = WXBizMsgCrypt(
        token=settings.WECOM_TOKEN,
        encoding_aes_key=settings.WECOM_ENCODING_AES_KEY,
        corp_id=settings.WECOM_CORP_ID
    )
    ret, reply_echostr = crypt.VerifyURL(msg_signature, timestamp, nonce, echostr)
    if ret != 0:
        raise SecurityError("企业微信签名验证失败")
    return reply_echostr
```

---

## 防攻击措施

### 限流（Rate Limiting）

```python
# 基于 Redis 的令牌桶限流
# app/core/middleware.py

RATE_LIMITS = {
    "/api/v1/chat/completion": "10/minute",    # 聊天接口：每分钟10次
    "/api/v1/auth/login": "5/minute",          # 登录接口：每分钟5次
    "/api/v1/knowledge/upload": "20/hour",     # 上传接口：每小时20次
    "default": "60/minute",                     # 默认：每分钟60次
}
```

### CORS 白名单

```python
# app/main.py
ALLOWED_ORIGINS = [
    settings.FRONTEND_URL,        # 管理后台域名
    settings.WIDGET_URL,          # 聊天组件域名
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # 不用 ["*"]
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "X-API-Key"],
)
```

### 输入校验

```python
# Pydantic 自动校验，额外需要注意：

# 1. 字符串长度限制
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    visitor_id: str = Field(..., pattern=r"^[a-zA-Z0-9\-]+$")

# 2. 文件上传限制
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}

# 3. SQL 注入防护
# SQLAlchemy 参数化查询自动防护，禁止拼接 SQL 字符串
# ❌ f"SELECT * FROM visitors WHERE name = '{name}'"
# ✅ select(Visitor).where(Visitor.name == name)
```

### HTTP 安全头

```python
# Nginx 配置
add_header X-Content-Type-Options nosniff;
add_header X-Frame-Options DENY;
add_header X-XSS-Protection "1; mode=block";
add_header Content-Security-Policy "default-src 'self'";
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
```

---

## 日志安全

### 不能记录的内容

```python
# ❌ 绝对不能出现在日志里
logger.info(f"API Key: {api_key}")
logger.info(f"密码: {password}")
logger.info(f"Token: {jwt_token}")

# ✅ 正确做法
logger.info("API Key 验证成功", api_key_suffix=api_key[-4:])
logger.info("用户登录", username=username)
```

### 必须记录的内容

| 事件 | 记录什么 |
|------|----------|
| 登录成功/失败 | 用户名、IP、时间 |
| API Key 创建/删除 | 操作人、Key 后4位 |
| 权限变更 | 操作人、变更内容 |
| 异常错误 | 完整 traceback（不含密钥） |
| 企业微信回调 | MsgId、时间戳（不含消息内容） |

---

## 安全检查清单（每次部署前）

- [ ] .env 文件不在 Git 仓库中
- [ ] SECRET_KEY 和 JWT_SECRET_KEY 是随机生成的强密码
- [ ] HTTPS 已启用（Let's Encrypt 证书有效）
- [ ] CORS 只允许白名单域名
- [ ] 限流已开启
- [ ] 数据库密码不是默认值
- [ ] Redis 设置了密码（如果暴露公网）
- [ ] Docker 容器不使用 root 用户运行
- [ ] 敏感接口需要认证才能访问
