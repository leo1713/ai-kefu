from __future__ import annotations

from collections.abc import AsyncGenerator

import structlog
from anthropic import APIConnectionError, APIStatusError, APITimeoutError, AsyncAnthropic
from anthropic.types import Message

from app.core.exceptions import ExternalServiceError

logger = structlog.get_logger()


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
