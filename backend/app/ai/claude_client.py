from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import structlog
from anthropic import APIConnectionError, APIStatusError, APITimeoutError, AsyncAnthropic
from anthropic.types import Message

from app.core.exceptions import ExternalServiceError

logger = structlog.get_logger()


class ToolCallResult:
    """tool_use 调用结果，从 Claude 的非流式或流式响应中解析出来。"""

    def __init__(self, tool_name: str, tool_input: dict[str, Any]) -> None:
        self.tool_name = tool_name
        self.tool_input = tool_input

    def __repr__(self) -> str:
        return f"ToolCallResult(tool={self.tool_name!r}, input={self.tool_input!r})"


class StreamWithToolResult:
    """
    流式响应容器：
    - text_chunks：AI 在触发工具前输出的文字片段（异步生成）
    - tool_call：如果触发了工具，则非 None
    """

    def __init__(self) -> None:
        self.text_chunks: list[str] = []
        self.tool_call: ToolCallResult | None = None


class ClaudeClient:
    def __init__(self, api_key: str, base_url: str = "") -> None:
        kwargs: dict[str, object] = {"api_key": api_key, "timeout": 30.0}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = AsyncAnthropic(**kwargs)  # type: ignore[arg-type]

    async def complete(
        self,
        messages: list[dict[str, str]],
        system: str = "",
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 2000,
    ) -> Message:
        try:
            return await self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,  # type: ignore[arg-type]
            )
        except APITimeoutError as e:
            logger.error("claude_timeout")
            raise ExternalServiceError("Claude API timeout") from e
        except APIConnectionError as e:
            logger.error("claude_connection_error", error=str(e))
            raise ExternalServiceError("Claude API connection error") from e
        except APIStatusError as e:
            logger.error("claude_api_error", status_code=e.status_code)
            raise ExternalServiceError(f"Claude API error: {e.status_code}") from e

    async def stream_text(
        self,
        messages: list[dict[str, str]],
        system: str = "",
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 2000,
    ) -> AsyncGenerator[str, None]:
        try:
            async with self._client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,  # type: ignore[arg-type]
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except APITimeoutError as e:
            logger.error("claude_stream_timeout")
            raise ExternalServiceError("Claude API timeout") from e
        except APIConnectionError as e:
            logger.error("claude_stream_connection_error", error=str(e))
            raise ExternalServiceError("Claude API connection error") from e
        except APIStatusError as e:
            logger.error("claude_stream_api_error", status_code=e.status_code)
            raise ExternalServiceError(f"Claude API error: {e.status_code}") from e

    async def stream_with_tools(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        system: str = "",
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 2000,
    ) -> tuple[AsyncGenerator[str, None], "StreamWithToolResult"]:
        """
        流式调用 + 工具支持。

        返回 (text_gen, result_holder)：
        - text_gen：异步生成器，逐块 yield 文字内容（消费完才会填充 result_holder）
        - result_holder：消费完 text_gen 后，tool_call 字段有值则说明 AI 触发了工具

        用法：
            gen, result = await client.stream_with_tools(messages, tools)
            async for chunk in gen:
                yield chunk       # 先输出文字
            if result.tool_call:  # 再检查工具
                handle(result.tool_call)
        """
        result = StreamWithToolResult()

        async def _gen() -> AsyncGenerator[str, None]:
            try:
                async with self._client.messages.stream(
                    model=model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=messages,  # type: ignore[arg-type]
                    tools=tools,  # type: ignore[arg-type]
                    tool_choice={"type": "auto"},
                ) as stream:
                    async for text in stream.text_stream:
                        result.text_chunks.append(text)
                        yield text

                    # 流结束后解析最终消息，检查是否有工具调用
                    final_msg = await stream.get_final_message()
                    for block in final_msg.content:
                        if block.type == "tool_use":
                            result.tool_call = ToolCallResult(
                                tool_name=block.name,
                                tool_input=dict(block.input),  # type: ignore[arg-type]
                            )
                            break
            except APITimeoutError as e:
                logger.error("claude_stream_with_tools_timeout")
                raise ExternalServiceError("Claude API timeout") from e
            except APIConnectionError as e:
                logger.error("claude_stream_with_tools_connection_error", error=str(e))
                raise ExternalServiceError("Claude API connection error") from e
            except APIStatusError as e:
                logger.error("claude_stream_with_tools_api_error", status_code=e.status_code)
                raise ExternalServiceError(f"Claude API error: {e.status_code}") from e

        return _gen(), result
