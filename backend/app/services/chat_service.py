from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.claude_client import ClaudeClient
from app.ai.streaming import sse
from app.ai.tools import HANDOFF_TOOL, HANDOFF_TOOL_NAME
from app.config import settings
from app.core.exceptions import ExternalServiceError
from app.models.conversation import Conversation
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
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conv = result.scalar_one_or_none() or await conversation_service.get_or_create_active(
            db, visitor.id
        )
    else:
        conv = await conversation_service.get_or_create_active(db, visitor.id)

    # 如果会话已转人工，不再调 AI，直接告知用户
    if conv.status == "transferred":
        user_msg = Message(
            conversation_id=conv.id,
            role="user",
            content=message,
            msg_type="text",
        )
        db.add(user_msg)
        await db.commit()

        notice = "您的问题已转接给人工客服，请稍候，客服人员将很快为您服务。"
        sys_msg = Message(
            conversation_id=conv.id,
            role="assistant",
            content=notice,
            msg_type="text",
        )
        db.add(sys_msg)
        await db.commit()
        await db.refresh(sys_msg)

        yield sse("chat.started", conversation_id=str(conv.id), visitor_id=str(visitor.id))
        yield sse("chat.content_chunk", text=notice)
        yield sse("chat.completed", message_id=str(sys_msg.id))
        return

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

    # RAG：检索相关知识库内容注入系统提示
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
        text_gen, tool_result = await client.stream_with_tools(
            messages=messages,
            tools=[HANDOFF_TOOL],  # type: ignore[list-item]
            system=system_prompt,
            model=agent.model,
            max_tokens=agent.max_tokens,
        )
        async for chunk in text_gen:
            full_text += chunk
            yield sse("chat.content_chunk", text=chunk)
    except ExternalServiceError as e:
        yield sse("chat.error", message=str(e))
        return

    # 保存 AI 回复（可能是空字符串，如果 AI 直接调工具未输出文字）
    if full_text:
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
    else:
        yield sse("chat.completed", message_id="")

    # 检查是否触发了 handoff 工具
    if tool_result.tool_call and tool_result.tool_call.tool_name == HANDOFF_TOOL_NAME:
        tool_input = tool_result.tool_call.tool_input
        reason: str = str(tool_input.get("reason", "AI 触发转人工"))
        summary: str = str(tool_input.get("summary", ""))

        logger.info(
            "chat_handoff_triggered",
            conversation_id=str(conv.id),
            reason=reason,
        )

        yield sse("chat.tool_call", tool="transfer_to_human", reason=reason, summary=summary)

        updated_conv = await conversation_service.transfer_conversation(
            db, conv.id, reason=reason, summary=summary
        )

        yield sse(
            "chat.handoff",
            conversation_id=str(conv.id),
            reason=reason,
            assigned_staff_id=(
                str(updated_conv.assigned_staff_id)
                if updated_conv.assigned_staff_id
                else None
            ),
        )

        logger.info(
            "chat_handoff_completed",
            conversation_id=str(conv.id),
            assigned_staff_id=str(updated_conv.assigned_staff_id)
            if updated_conv.assigned_staff_id
            else None,
        )
