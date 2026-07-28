from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from unittest.mock import MagicMock, patch

from httpx import AsyncClient


async def _stream(chunks: list[str]) -> AsyncGenerator[str, None]:
    for c in chunks:
        yield c


async def test_rag_grounded_answer(client: AsyncClient) -> None:
    rag_chunks = [
        {"id": str(uuid.uuid4()), "document_name": "policy.txt",
         "content": "退款政策：7天无理由退款。", "score": 0.95}
    ]

    with (
        patch("app.services.rag_service.search_chunks", return_value=rag_chunks),
        patch("app.services.chat_service.ClaudeClient") as mock_cls,
    ):
        mock_instance = MagicMock()
        mock_instance.stream_text = MagicMock(return_value=_stream(["根据", "退款政策", "可以退款"]))
        mock_cls.return_value = mock_instance

        response = await client.post(
            "/api/v1/chat/completion",
            json={"message": "退款政策是什么", "visitor_id": "rag-test"},
        )

    assert response.status_code == 200
    body = response.content.decode()
    assert "chat.completed" in body

    # Verify system prompt contained RAG context
    call_kwargs = mock_instance.stream_text.call_args.kwargs
    assert "退款政策" in call_kwargs["system"]
