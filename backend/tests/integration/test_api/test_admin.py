from __future__ import annotations

from httpx import AsyncClient


async def test_api_key_encrypted(client: AsyncClient) -> None:
    plain_key = "sk-ant-testkey123456"

    r = await client.post(
        "/api/v1/admin/settings/api-key", json={"api_key": plain_key}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "saved"

    r2 = await client.get("/api/v1/admin/settings")
    assert r2.status_code == 200
    data = r2.json()
    assert data["anthropic_api_key"] is not None
    assert data["anthropic_api_key"] != plain_key
    assert "***" in data["anthropic_api_key"]


async def test_settings_empty_before_save(client: AsyncClient) -> None:
    r = await client.get("/api/v1/admin/settings")
    assert r.status_code == 200
