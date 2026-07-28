from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.exceptions import ExternalServiceError

# ── helpers ───────────────────────────────────────────────────────────────────

async def _collect(gen: AsyncGenerator[str, None]) -> list[str]:
    return [item async for item in gen]


def _make_message(role: str, content: str) -> object:
    m = MagicMock()
    m.role = role
    m.content = content
    return m


# ── test_context_memory (1.2.6) ───────────────────────────────────────────────

async def test_context_memory() -> None:
    from app.services.chat_service import chat_stream

    history = [_make_message("user" if i % 2 == 0 else "assistant", f"msg {i}") for i in range(20)]

    captured_messages: list[dict[str, str]] = []

    async def fake_stream(**kwargs: object) -> AsyncGenerator[str, None]:
        captured_messages.extend(kwargs.get("messages", []))  # type: ignore[arg-type]
        yield "ok"

    visitor = MagicMock()
    visitor.id = uuid.uuid4()
    conv = MagicMock()
    conv.id = uuid.uuid4()
    agent = MagicMock()
    agent.system_prompt = ""
    agent.model = "test"
    agent.max_tokens = 100
    db = AsyncMock()
    db.add = MagicMock()

    with (
        patch("app.services.chat_service.visitor_service.get_or_create", return_value=visitor),
        patch(
            "app.services.chat_service.conversation_service.get_or_create_active",
            return_value=conv,
        ),
        patch(
            "app.services.chat_service.conversation_service.get_recent_messages",
            return_value=history,
        ),
        patch("app.services.chat_service.seed_default_agent", return_value=agent),
        patch("app.services.chat_service.ClaudeClient") as mock_cls,
    ):
        mock_instance = MagicMock()
        mock_instance.stream_text = MagicMock(side_effect=fake_stream)
        mock_cls.return_value = mock_instance

        await _collect(chat_stream(db, "test-visitor", "new message"))

    # 20 history msgs + 1 new user message = 21 total sent to Claude
    assert len(captured_messages) == 21
    assert captured_messages[-1]["role"] == "user"
    assert captured_messages[-1]["content"] == "new message"


# ── test_error_handling (1.2.7) ───────────────────────────────────────────────

async def test_error_handling_invalid_key() -> None:
    from app.services.chat_service import chat_stream

    visitor = MagicMock()
    visitor.id = uuid.uuid4()
    conv = MagicMock()
    conv.id = uuid.uuid4()
    agent = MagicMock()
    agent.system_prompt = ""
    agent.model = "test"
    agent.max_tokens = 100
    db = AsyncMock()
    db.add = MagicMock()

    async def raise_auth_error(**kwargs: object) -> AsyncGenerator[str, None]:
        raise ExternalServiceError("Claude API error: 401")
        yield  # make it a generator

    with (
        patch("app.services.chat_service.visitor_service.get_or_create", return_value=visitor),
        patch(
            "app.services.chat_service.conversation_service.get_or_create_active",
            return_value=conv,
        ),
        patch(
            "app.services.chat_service.conversation_service.get_recent_messages",
            return_value=[],
        ),
        patch("app.services.chat_service.seed_default_agent", return_value=agent),
        patch("app.services.chat_service.ClaudeClient") as mock_cls,
    ):
        mock_instance = MagicMock()
        mock_instance.stream_text = MagicMock(side_effect=raise_auth_error)
        mock_cls.return_value = mock_instance

        events = await _collect(chat_stream(db, "test-visitor", "hello"))

    event_types = [e.split('"event": "')[1].split('"')[0] for e in events if '"event"' in e]
    assert "chat.error" in event_types
    assert "chat.completed" not in event_types


async def test_error_handling_timeout() -> None:
    from app.services.chat_service import chat_stream

    visitor = MagicMock()
    visitor.id = uuid.uuid4()
    conv = MagicMock()
    conv.id = uuid.uuid4()
    agent = MagicMock()
    agent.system_prompt = ""
    agent.model = "test"
    agent.max_tokens = 100
    db = AsyncMock()
    db.add = MagicMock()

    async def raise_timeout(**kwargs: object) -> AsyncGenerator[str, None]:
        raise ExternalServiceError("Claude API timeout")
        yield

    with (
        patch("app.services.chat_service.visitor_service.get_or_create", return_value=visitor),
        patch(
            "app.services.chat_service.conversation_service.get_or_create_active",
            return_value=conv,
        ),
        patch(
            "app.services.chat_service.conversation_service.get_recent_messages",
            return_value=[],
        ),
        patch("app.services.chat_service.seed_default_agent", return_value=agent),
        patch("app.services.chat_service.ClaudeClient") as mock_cls,
    ):
        mock_instance = MagicMock()
        mock_instance.stream_text = MagicMock(side_effect=raise_timeout)
        mock_cls.return_value = mock_instance

        events = await _collect(chat_stream(db, "test-visitor", "hello"))

    event_types = [e.split('"event": "')[1].split('"')[0] for e in events if '"event"' in e]
    assert "chat.error" in event_types
