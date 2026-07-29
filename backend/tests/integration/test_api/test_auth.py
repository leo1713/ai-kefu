from __future__ import annotations

from httpx import AsyncClient


async def test_login_returns_token(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/init-admin")
    r = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 20


async def test_login_wrong_password_returns_401(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/init-admin")
    r = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrongpassword"},
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "AUTHENTICATION_ERROR"


async def test_login_unknown_user_returns_401(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/auth/login",
        json={"username": "nonexistent", "password": "anything"},
    )
    assert r.status_code == 401
