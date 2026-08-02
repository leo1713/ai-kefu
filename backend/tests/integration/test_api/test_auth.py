"""
认证接口集成测试。

init-admin 现在受 ALLOW_INIT_ADMIN + DEFAULT_ADMIN_PASSWORD 控制，
测试中通过 mock service 层绕过配置限制，不依赖真实数据库和环境变量。
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from app.models.staff import Staff
from httpx import AsyncClient


async def test_login_returns_token(client: AsyncClient) -> None:
    with patch(
        "app.services.auth_service.login",
        new=AsyncMock(return_value="fake.jwt.token"),
    ):
        r = await client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "somepassword"},
        )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["access_token"] == "fake.jwt.token"


async def test_login_wrong_password_returns_401(client: AsyncClient) -> None:
    from app.core.exceptions import AuthenticationError

    with patch(
        "app.services.auth_service.login",
        side_effect=AuthenticationError("用户名或密码错误"),
    ):
        r = await client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrongpassword"},
        )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "AUTHENTICATION_ERROR"


async def test_login_unknown_user_returns_401(client: AsyncClient) -> None:
    from app.core.exceptions import AuthenticationError

    with patch(
        "app.services.auth_service.login",
        side_effect=AuthenticationError("用户名或密码错误"),
    ):
        r = await client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent", "password": "anything"},
        )
    assert r.status_code == 401


async def test_init_admin_blocked_without_flag(client: AsyncClient) -> None:
    """init-admin 在 ALLOW_INIT_ADMIN=false 时应返回 403。"""
    from app.core.exceptions import PermissionError

    with patch(
        "app.services.auth_service.seed_default_admin",
        side_effect=PermissionError("init-admin 未启用"),
    ):
        r = await client.post("/api/v1/auth/init-admin")
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "PERMISSION_ERROR"


async def test_init_admin_success(client: AsyncClient) -> None:
    """ALLOW_INIT_ADMIN=true 时 init-admin 返回 201 和用户信息。"""
    fake_staff = MagicMock(spec=Staff)
    fake_staff.username = "admin"
    fake_staff.display_name = "管理员"

    with patch(
        "app.services.auth_service.seed_default_admin",
        new=AsyncMock(return_value=fake_staff),
    ):
        r = await client.post("/api/v1/auth/init-admin")
    assert r.status_code == 201
    assert r.json()["username"] == "admin"
