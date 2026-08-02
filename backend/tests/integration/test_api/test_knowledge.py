from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

_FAKE_VECTOR = [0.1] * 1536


@pytest.fixture
def mock_embed() -> AsyncGenerator[None, None]:
    with patch("app.services.rag_service.embed_text", new=AsyncMock(return_value=_FAKE_VECTOR)):
        yield


async def test_embedding_stored(auth_client: AsyncClient, mock_embed: None) -> None:
    response = await auth_client.post(
        "/api/v1/knowledge/upload",
        files={"file": ("embed_test.txt", b"Refund policy: returns accepted within 7 days.", "text/plain")},
    )
    assert response.status_code == 201
    data = response.json()
    assert uuid.UUID(data["id"])
    assert data["status"] == "done"


async def test_upload_creates_chunks(auth_client: AsyncClient, mock_embed: None) -> None:
    long_text = ("知识库测试内容，包含退款政策和售后服务信息。" * 20).encode()
    response = await auth_client.post(
        "/api/v1/knowledge/upload",
        files={"file": ("big.txt", long_text, "text/plain")},
    )
    assert response.status_code == 201
    assert uuid.UUID(response.json()["id"])


# ── CRUD tests (1.3.7) ────────────────────────────────────────────────────────


async def test_create_and_list_collection(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        "/api/v1/knowledge/collections",
        json={"name": "测试集合", "description": "单元测试"},
    )
    assert r.status_code == 201
    coll_id = r.json()["id"]

    listing = await auth_client.get("/api/v1/knowledge/collections")
    assert listing.status_code == 200
    ids = [c["id"] for c in listing.json()]
    assert coll_id in ids


async def test_delete_collection(auth_client: AsyncClient) -> None:
    r = await auth_client.post("/api/v1/knowledge/collections", json={"name": "待删除集合"})
    assert r.status_code == 201
    coll_id = r.json()["id"]

    del_r = await auth_client.delete(f"/api/v1/knowledge/collections/{coll_id}")
    assert del_r.status_code == 204

    listing = await auth_client.get("/api/v1/knowledge/collections")
    assert coll_id not in [c["id"] for c in listing.json()]


async def test_list_and_delete_document(auth_client: AsyncClient, mock_embed: None) -> None:
    upload = await auth_client.post(
        "/api/v1/knowledge/upload",
        files={"file": ("crud_test.txt", b"CRUD test content", "text/plain")},
    )
    assert upload.status_code == 201
    doc_id = upload.json()["id"]

    docs = await auth_client.get("/api/v1/knowledge/documents")
    assert docs.status_code == 200
    assert doc_id in [d["id"] for d in docs.json()]

    del_r = await auth_client.delete(f"/api/v1/knowledge/documents/{doc_id}")
    assert del_r.status_code == 204

    docs_after = await auth_client.get("/api/v1/knowledge/documents")
    assert doc_id not in [d["id"] for d in docs_after.json()]
