from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.claude_client import ClaudeClient
from app.ai.streaming import sse
from app.config import settings
from app.core.exceptions import ExternalServiceError
from app.models.message import Message
from app.services import conversation_service, rag_service, visitor_service
from app.services.agent_service import seed_default_agent

logger = structlog.get_logger()


async def chat_stream(
    db: AsyncSession,
    visitor_id: str,
    message: str,
    agent_id: uuid.UUID | None = None,
    conversation_id: uuid.UUID | None = None,
) -> AsyncGenerator[str, None]:
    visitor = await visitor_service.get_or_create(db, visitor_id)

    if conversation_id:
        from sqlalchemy import select

        from app.models.conversation import Conversation
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conv = result.scalar_one_or_none() or await conversation_service.get_or_create_active(
            db, visitor.id
        )
    else:
        conv = await conversation_service.get_or_create_active(db, visitor.id)

    agent = await seed_default_agent(db)

    history = await conversation_service.get_recent_messages(db, conv.id, limit=20)
    messages: list[dict[str, str]] = [
        {"role": msg.role, "content": msg.content} for msg in history
    ]
    messages.append({"role": "user", "content": message})

    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=message,
        msg_type="text",
    )
    db.add(user_msg)
    await db.commit()
    await db.refresh(user_msg)

    yield sse(
        "chat.started",
        conversation_id=str(conv.id),
        visitor_id=str(visitor.id),
    )

    # RAG: retrieve relevant context and inject into system prompt
    rag_results = await rag_service.search_chunks(db, message, top_k=3)
    system_prompt = agent.system_prompt
    if rag_results:
        context = "\n\n".join(f"[知识库] {r['content']}" for r in rag_results)
        system_prompt = f"{system_prompt}\n\n以下是相关知识库内容，请优先参考：\n{context}"

    client = ClaudeClient(
        api_key=settings.anthropic_api_key,
        base_url=settings.anthropic_base_url,
    )
    full_text = ""

    try:
        async for chunk in client.stream_text(
            messages=messages,
            system=system_prompt,
            model=agent.model,
            max_tokens=agent.max_tokens,
        ):
            full_text += chunk
            yield sse("chat.content_chunk", text=chunk)
    except ExternalServiceError as e:
        yield sse("chat.error", message=str(e))
        return

    assistant_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=full_text,
        msg_type="text",
    )
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)

    yield sse("chat.completed", message_id=str(assistant_msg.id))
