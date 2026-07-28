from __future__ import annotations

import contextlib
import json
import uuid
from collections.abc import AsyncGenerator
from unittest.mock import MagicMock, patch

from httpx import AsyncClient


async def _mock_stream(chunks: list[str]) -> AsyncGenerator[str, None]:
    for chunk in chunks:
        yield chunk


def _patch_claude(chunks: list[str] = None) -> object:
    if chunks is None:
        chunks = ["你", "好", "！"]

    mock_cls = MagicMock()
    mock_instance = MagicMock()
    mock_instance.stream_text = MagicMock(return_value=_mock_stream(chunks))
    mock_cls.return_value = mock_instance
    return patch("app.services.chat_service.ClaudeClient", mock_cls)


async def _collect_events(response_content: bytes) -> list[dict]:
    events = []
    for line in response_content.decode().split("\n"):
        if line.startswith("data: "):
            with contextlib.suppress(json.JSONDecodeError):
                events.append(json.loads(line[6:]))
    return events


async def test_message_persisted(client: AsyncClient) -> None:
    with _patch_claude(["消", "息", "已", "存", "库"]):
        response = await client.post(
            "/api/v1/chat/completion",
            json={"message": "持久化测试", "visitor_id": "persist-test"},
        )

    assert response.status_code == 200
    events = await _collect_events(response.content)

    completed = next((e for e in events if e["event"] == "chat.completed"), None)
    assert completed is not None, "chat.completed event not found"
    assert uuid.UUID(completed["message_id"])
