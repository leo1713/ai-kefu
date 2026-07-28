import uuid

from httpx import AsyncClient


async def test_create_agent_returns_201(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/agents",
        json={"name": "集成测试客服", "system_prompt": "测试提示词"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "集成测试客服"
    assert data["system_prompt"] == "测试提示词"
    assert uuid.UUID(data["id"])


async def test_list_agents_returns_list(client: AsyncClient) -> None:
    response = await client.get("/api/v1/agents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


async def test_get_agent_by_id(client: AsyncClient) -> None:
    create = await client.post("/api/v1/agents", json={"name": "查询测试Agent"})
    assert create.status_code == 201
    agent_id = create.json()["id"]

    response = await client.get(f"/api/v1/agents/{agent_id}")
    assert response.status_code == 200
    assert response.json()["id"] == agent_id


async def test_get_agent_not_found_returns_404(client: AsyncClient) -> None:
    fake_id = uuid.uuid4()
    response = await client.get(f"/api/v1/agents/{fake_id}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


async def test_seed_default_agent_via_api(client: AsyncClient) -> None:
    response = await client.post("/api/v1/agents/seed")
    assert response.status_code == 201
    data = response.json()
    assert data["is_default"] is True
    assert data["name"] == "默认客服"


async def test_seed_is_idempotent(client: AsyncClient) -> None:
    r1 = await client.post("/api/v1/agents/seed")
    r2 = await client.post("/api/v1/agents/seed")
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]


async def test_seed_via_api(client: AsyncClient) -> None:
    response = await client.post("/api/v1/agents/seed")
    assert response.status_code == 201
    assert response.json()["is_default"] is True

