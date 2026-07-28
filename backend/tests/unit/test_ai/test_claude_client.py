from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anthropic import APIStatusError, APITimeoutError
from anthropic.types import Message, TextBlock, Usage
from app.ai.claude_client import ClaudeClient
from app.core.exceptions import ExternalServiceError


def _make_message(text: str = "你好！") -> Message:
    return Message(
        id="msg_test123",
        type="message",
        role="assistant",
        content=[TextBlock(type="text", text=text)],
        model="claude-sonnet-4-20250514",
        stop_reason="end_turn",
        stop_sequence=None,
        usage=Usage(input_tokens=10, output_tokens=5),
    )


class _MockTextStream:
    def __init__(self, chunks: list[str]) -> None:
        self._iter: AsyncIterator[str] = aiter(self._gen(chunks))

    @staticmethod
    async def _gen(chunks: list[str]) -> AsyncIterator[str]:
        for chunk in chunks:
            yield chunk

    def __aiter__(self) -> AsyncIterator[str]:
        return self._iter

    async def __anext__(self) -> str:
        return await self._iter.__anext__()


class _MockStreamCtx:
    def __init__(self, chunks: list[str]) -> None:
        self.text_stream = _MockTextStream(chunks)

    async def __aenter__(self) -> _MockStreamCtx:
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass


@pytest.fixture
def client() -> ClaudeClient:
    with patch("app.ai.claude_client.AsyncAnthropic"):
        c = ClaudeClient(api_key="test-key")
    return c


# ── complete() ────────────────────────────────────────────────────────────────

async def test_complete_returns_message(client: ClaudeClient) -> None:
    expected = _make_message("你好！有什么可以帮您？")
    client._client.messages.create = AsyncMock(return_value=expected)  # type: ignore[attr-defined]

    result = await client.complete(
        messages=[{"role": "user", "content": "你好"}],
        system="你是AI客服",
    )

    assert result.content[0].text == "你好！有什么可以帮您？"
    client._client.messages.create.assert_called_once()  # type: ignore[attr-defined]


async def test_complete_passes_correct_params(client: ClaudeClient) -> None:
    client._client.messages.create = AsyncMock(return_value=_make_message())  # type: ignore[attr-defined]

    await client.complete(
        messages=[{"role": "user", "content": "hi"}],
        system="system prompt",
        model="claude-sonnet-4-20250514",
        max_tokens=500,
    )

    call_kwargs = client._client.messages.create.call_args.kwargs  # type: ignore[attr-defined]
    assert call_kwargs["model"] == "claude-sonnet-4-20250514"
    assert call_kwargs["max_tokens"] == 500
    assert call_kwargs["system"] == "system prompt"


async def test_complete_raises_on_timeout(client: ClaudeClient) -> None:
    client._client.messages.create = AsyncMock(side_effect=APITimeoutError(request=MagicMock()))  # type: ignore[attr-defined]

    with pytest.raises(ExternalServiceError, match="timeout"):
        await client.complete(messages=[{"role": "user", "content": "hi"}])


async def test_complete_raises_on_api_error(client: ClaudeClient) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 401
    client._client.messages.create = AsyncMock(  # type: ignore[attr-defined]
        side_effect=APIStatusError(
            "Unauthorized", response=mock_response, body={"error": {"type": "auth"}}
        )
    )

    with pytest.raises(ExternalServiceError, match="401"):
        await client.complete(messages=[{"role": "user", "content": "hi"}])


# ── stream_text() ─────────────────────────────────────────────────────────────

async def test_stream_text_yields_chunks(client: ClaudeClient) -> None:
    chunks = ["你", "好", "！"]
    client._client.messages.stream = MagicMock(return_value=_MockStreamCtx(chunks))  # type: ignore[attr-defined]

    result: list[str] = []
    async for text in client.stream_text(
        messages=[{"role": "user", "content": "你好"}],
        system="你是客服",
    ):
        result.append(text)

    assert result == chunks


async def test_stream_text_raises_on_timeout(client: ClaudeClient) -> None:
    client._client.messages.stream = MagicMock(  # type: ignore[attr-defined]
        side_effect=APITimeoutError(request=MagicMock())
    )

    with pytest.raises(ExternalServiceError, match="timeout"):
        async for _ in client.stream_text(messages=[{"role": "user", "content": "hi"}]):
            pass
