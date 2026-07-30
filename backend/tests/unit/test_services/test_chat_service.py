from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

from app.ai.claude_client import StreamWithToolResult
from app.core.exceptions import ExternalServiceError

# ── helpers ───────────────────────────────────────────────────────────────────


async def _collect(gen: AsyncGenerator[str, None]) -> list[str]:
    return [item async for item in gen]


def _make_message(role: str, content: str) -> object:
    m = MagicMock()
    m.role = role
    m.content = content
    return m


def _make_conv(status: str = "active") -> MagicMock:
    conv = MagicMock()
    conv.id = uuid.uuid4()
    conv.status = status
    return conv


def _make_stream_with_tools_mock(chunks: list[str]) -> AsyncMock:
    """返回一个模拟 stream_with_tools 的 AsyncMock。

    stream_with_tools 是 async def，返回 (AsyncGenerator, StreamWithToolResult)。
    """
    result = StreamWithToolResult()

    async def _gen() -> AsyncGenerator[str, None]:
        for c in chunks:
            yield c

    mock = AsyncMock(return_value=(_gen(), result))
    return mock


def _make_handoff_stream_mock(
    chunks: list[str], reason: str, summary: str
) -> AsyncMock:
    """返回触发了 handoff 工具的 stream_with_tools mock。"""
    from app.ai.claude_client import ToolCallResult

    result = StreamWithToolResult()
    result.tool_call = ToolCallResult(
        tool_name="transfer_to_human",
        tool_input={"reason": reason, "summary": summary},
    )

    async def _gen() -> AsyncGenerator[str, None]:
        for c in chunks:
            yield c

    mock = AsyncMock(return_value=(_gen(), result))
    return mock


_NO_RAG = patch(
    "app.services.chat_service.rag_service.search_chunks",
    new=AsyncMock(return_value=[]),
)


# ── test_context_memory (1.2.6) ───────────────────────────────────────────────


async def test_context_memory() -> None:
    from app.services.chat_service import chat_stream

    history = [
        _make_message("user" if i % 2 == 0 else "assistant", f"msg {i}")
        for i in range(20)
    ]
    captured_messages: list[dict[str, str]] = []

    async def fake_stream_with_tools(**kwargs: object) -> tuple[AsyncGenerator[str, None], StreamWithToolResult]:
        captured_messages.extend(kwargs.get("messages", []))  # type: ignore[arg-type]

        async def _gen() -> AsyncGenerator[str, None]:
            yield "ok"

        return _gen(), StreamWithToolResult()

    visitor = MagicMock()
    visitor.id = uuid.uuid4()
    conv = _make_conv()
    agent = MagicMock()
    agent.system_prompt = ""
    agent.model = "test"
    agent.max_tokens = 100
    db = AsyncMock()
    db.add = MagicMock()

    with (
        _NO_RAG,
        patch(
            "app.services.chat_service.visitor_service.get_or_create",
            return_value=visitor,
        ),
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
        mock_instance.stream_with_tools = AsyncMock(side_effect=fake_stream_with_tools)
        mock_cls.return_value = mock_instance
        await _collect(chat_stream(db, "test-visitor", "new message"))

    # history(20) + new user message(1) = 21
    assert len(captured_messages) == 21
    assert captured_messages[-1]["role"] == "user"
    assert captured_messages[-1]["content"] == "new message"


# ── test_error_handling (1.2.7) ───────────────────────────────────────────────


async def test_error_handling_invalid_key() -> None:
    from app.services.chat_service import chat_stream

    visitor = MagicMock()
    visitor.id = uuid.uuid4()
    conv = _make_conv()
    agent = MagicMock()
    agent.system_prompt = ""
    agent.model = "test"
    agent.max_tokens = 100
    db = AsyncMock()
    db.add = MagicMock()

    async def raise_auth_error(**kwargs: object) -> tuple[AsyncGenerator[str, None], StreamWithToolResult]:
        raise ExternalServiceError("Claude API error: 401")

    with (
        _NO_RAG,
        patch(
            "app.services.chat_service.visitor_service.get_or_create",
            return_value=visitor,
        ),
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
        mock_instance.stream_with_tools = AsyncMock(side_effect=raise_auth_error)
        mock_cls.return_value = mock_instance
        events = await _collect(chat_stream(db, "test-visitor", "hello"))

    event_types = [
        e.split('"event": "')[1].split('"')[0] for e in events if '"event"' in e
    ]
    assert "chat.error" in event_types
    assert "chat.completed" not in event_types


async def test_error_handling_timeout() -> None:
    from app.services.chat_service import chat_stream

    visitor = MagicMock()
    visitor.id = uuid.uuid4()
    conv = _make_conv()
    agent = MagicMock()
    agent.system_prompt = ""
    agent.model = "test"
    agent.max_tokens = 100
    db = AsyncMock()
    db.add = MagicMock()

    async def raise_timeout(**kwargs: object) -> tuple[AsyncGenerator[str, None], StreamWithToolResult]:
        raise ExternalServiceError("Claude API timeout")

    with (
        _NO_RAG,
        patch(
            "app.services.chat_service.visitor_service.get_or_create",
            return_value=visitor,
        ),
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
        mock_instance.stream_with_tools = AsyncMock(side_effect=raise_timeout)
        mock_cls.return_value = mock_instance
        events = await _collect(chat_stream(db, "test-visitor", "hello"))

    event_types = [
        e.split('"event": "')[1].split('"')[0] for e in events if '"event"' in e
    ]
    assert "chat.error" in event_types


# ── test_transferred_conversation ─────────────────────────────────────────────


async def test_transferred_conversation_returns_notice() -> None:
    """已转人工的会话应直接返回等待提示，不调 AI。"""
    from app.services.chat_service import chat_stream

    visitor = MagicMock()
    visitor.id = uuid.uuid4()
    conv = _make_conv(status="transferred")
    db = AsyncMock()
    db.add = MagicMock()

    with (
        patch(
            "app.services.chat_service.visitor_service.get_or_create",
            return_value=visitor,
        ),
        patch(
            "app.services.chat_service.conversation_service.get_or_create_active",
            return_value=conv,
        ),
        patch("app.services.chat_service.ClaudeClient") as mock_cls,
    ):
        events = await _collect(chat_stream(db, "test-visitor", "在吗"))

    # 不应该调用 AI
    mock_cls.assert_not_called()

    # 应该包含 chat.started 和 chat.completed
    event_types = [
        e.split('"event": "')[1].split('"')[0] for e in events if '"event"' in e
    ]
    assert "chat.started" in event_types
    assert "chat.completed" in event_types
    assert "chat.error" not in event_types

    # 回复内容应包含等待提示
    content_chunks = [e for e in events if '"event": "chat.content_chunk"' in e]
    assert len(content_chunks) == 1
    assert "人工客服" in content_chunks[0] or "请稍候" in content_chunks[0]


# ── test_handoff_triggered ────────────────────────────────────────────────────


async def test_handoff_triggered_emits_handoff_event() -> None:
    """AI 触发 transfer_to_human 工具后，应 emit chat.handoff 事件并更新会话状态。"""
    from app.services.chat_service import chat_stream

    visitor = MagicMock()
    visitor.id = uuid.uuid4()
    conv = _make_conv(status="active")
    agent = MagicMock()
    agent.system_prompt = ""
    agent.model = "test"
    agent.max_tokens = 100
    db = AsyncMock()
    db.add = MagicMock()

    updated_conv = _make_conv(status="transferred")
    updated_conv.assigned_staff_id = None

    with (
        _NO_RAG,
        patch(
            "app.services.chat_service.visitor_service.get_or_create",
            return_value=visitor,
        ),
        patch(
            "app.services.chat_service.conversation_service.get_or_create_active",
            return_value=conv,
        ),
        patch(
            "app.services.chat_service.conversation_service.get_recent_messages",
            return_value=[],
        ),
        patch("app.services.chat_service.seed_default_agent", return_value=agent),
        patch(
            "app.services.chat_service.conversation_service.transfer_conversation",
            new=AsyncMock(return_value=updated_conv),
        ) as mock_transfer,
        patch("app.services.chat_service.ClaudeClient") as mock_cls,
    ):
        mock_instance = MagicMock()
        mock_instance.stream_with_tools = _make_handoff_stream_mock(
            chunks=["正在为您转接人工客服..."],
            reason="用户要求退款，需要人工处理",
            summary="用户咨询退款流程",
        )
        mock_cls.return_value = mock_instance
        events = await _collect(
            chat_stream(db, "test-visitor", "我要退款，帮我转人工")
        )

    # 应该调用了 transfer_conversation
    mock_transfer.assert_called_once()
    call_kwargs = mock_transfer.call_args.kwargs
    assert call_kwargs["reason"] == "用户要求退款，需要人工处理"

    # 应该 emit chat.handoff 事件
    event_types = [
        e.split('"event": "')[1].split('"')[0] for e in events if '"event"' in e
    ]
    assert "chat.tool_call" in event_types
    assert "chat.handoff" in event_types


async def test_handoff_not_triggered_normal_chat() -> None:
    """正常对话不应触发 handoff。"""
    from app.services.chat_service import chat_stream

    visitor = MagicMock()
    visitor.id = uuid.uuid4()
    conv = _make_conv(status="active")
    agent = MagicMock()
    agent.system_prompt = ""
    agent.model = "test"
    agent.max_tokens = 100
    db = AsyncMock()
    db.add = MagicMock()

    with (
        _NO_RAG,
        patch(
            "app.services.chat_service.visitor_service.get_or_create",
            return_value=visitor,
        ),
        patch(
            "app.services.chat_service.conversation_service.get_or_create_active",
            return_value=conv,
        ),
        patch(
            "app.services.chat_service.conversation_service.get_recent_messages",
            return_value=[],
        ),
        patch("app.services.chat_service.seed_default_agent", return_value=agent),
        patch(
            "app.services.chat_service.conversation_service.transfer_conversation",
        ) as mock_transfer,
        patch("app.services.chat_service.ClaudeClient") as mock_cls,
    ):
        mock_instance = MagicMock()
        mock_instance.stream_with_tools = _make_stream_with_tools_mock(
            chunks=["您好，有什么可以帮您？"]
        )
        mock_cls.return_value = mock_instance
        events = await _collect(chat_stream(db, "test-visitor", "你好"))

    # 没有触发工具，不应调用 transfer_conversation
    mock_transfer.assert_not_called()

    event_types = [
        e.split('"event": "')[1].split('"')[0] for e in events if '"event"' in e
    ]
    assert "chat.handoff" not in event_types
    assert "chat.completed" in event_types
