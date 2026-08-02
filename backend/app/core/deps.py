"""
FastAPI 依赖注入：公共 Depends 函数。

当前导出：
- get_current_user：从 Bearer token 解析当前登录的 Staff，无效时返回 401。
"""
from __future__ import annotations

import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError
from app.database import get_db
from app.models.staff import Staff
from app.services import staff_service

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> Staff:
    """
    解析 Authorization: Bearer <token>，返回当前登录的 Staff 对象。

    失败情形（均返回 401）：
    - 缺少 Authorization header
    - token 签名无效或已过期
    - token 对应的 staff 不存在或已被禁用
    """
    if creds is None:
        raise AuthenticationError("缺少 Authorization header")

    from app.core.security import decode_access_token

    try:
        payload = decode_access_token(creds.credentials)
    except AuthenticationError:
        raise
    except Exception as exc:
        raise AuthenticationError("token 无效或已过期") from exc

    try:
        staff_id = uuid.UUID(str(payload["sub"]))
    except (KeyError, ValueError) as exc:
        raise AuthenticationError("token payload 格式错误") from exc

    staff = await staff_service.get_staff(db, staff_id)
    if not staff.is_active:
        raise AuthenticationError("账号已被禁用")

    return staff
