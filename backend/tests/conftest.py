"""
共享测试 fixtures。

- client：匿名 HTTP 客户端（测试公开接口用，如 /health、/auth/login）
- auth_client：带 Bearer token 的 HTTP 客户端（测试需要鉴权的接口）

集成测试需要真实 PostgreSQL（通过 Docker Compose 启动）。
单元测试用 mock，不需要数据库。
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.security import create_access_token
from app.main import app
from app.models.staff import Staff
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def auth_client() -> AsyncGenerator[AsyncClient, None]:
    """
    带有效 Bearer token 的 HTTP 客户端。

    直接用 create_access_token 生成 token（绕过数据库），
    同时 mock staff_service.get_staff，避免集成测试中需要真实 staff 记录。
    """
    fake_staff_id = uuid.uuid4()
    token = create_access_token({"sub": str(fake_staff_id), "username": "test_admin"})

    fake_staff = MagicMock(spec=Staff)
    fake_staff.id = fake_staff_id
    fake_staff.username = "test_admin"
    fake_staff.is_active = True

    with patch(
        "app.services.staff_service.get_staff",
        new=AsyncMock(return_value=fake_staff),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {token}"},
        ) as c:
            yield c
