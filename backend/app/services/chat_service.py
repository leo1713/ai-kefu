from __future__ import annotations

import json
import uuid
from collections.abc import AsyncGenerator

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.claude_client import ClaudeClient
from app.ai.specialists import SPECIALIST_AGENTS
from app.ai.streaming import sse
from app.ai.tools import ALL_TOOLS, HANDOFF_TOOL_NAME, QUERY_TOOL_NAMES, ROUTE_TO_AGENT_TOOL_NAME, SPECIALIST_TOOLS
from app.config import settings
from app.core.exceptions import ExternalServiceError
from app.models.conversation import Conversation
from app.models.message import Message
from app.services import conversation_service, rag_service, tools_service, visitor_service
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

    # --- agentic tool loop (max 5 iterations) ---
    loop_messages = list(messages)
    full_text = ""
    last_tool_call = None

    for _iteration in range(5):
        try:
            text_gen, tool_result = await client.stream_with_tools(
                messages=loop_messages,
                tools=ALL_TOOLS,  # type: ignore[arg-type]
                system=system_prompt,
                model=agent.model,
                max_tokens=agent.max_tokens,
            )
            iter_text = ""
            async for chunk in text_gen:
                iter_text += chunk
                yield sse("chat.content_chunk", text=chunk)
        except ExternalServiceError as e:
            yield sse("chat.error", message=str(e))
            return

        full_text += iter_text
        last_tool_call = tool_result.tool_call

        if not last_tool_call:
            break

        if last_tool_call.tool_name == HANDOFF_TOOL_NAME:
            break

        if last_tool_call.tool_name == ROUTE_TO_AGENT_TOOL_NAME:
            break

        if last_tool_call.tool_name in QUERY_TOOL_NAMES:
            yield sse("chat.tool_call", tool=last_tool_call.tool_name)
            tool_response = await tools_service.execute_tool(
                last_tool_call.tool_name, last_tool_call.tool_input
            )
            logger.info(
                "tool_executed",
                tool=last_tool_call.tool_name,
                input=last_tool_call.tool_input,
            )
            # Build multi-turn: assistant turn with tool_use, then tool_result
            assistant_content: list[dict[str, object]] = []
            if iter_text:
                assistant_content.append({"type": "text", "text": iter_text})
            assistant_content.append({
                "type": "tool_use",
                "id": last_tool_call.tool_use_id,
                "name": last_tool_call.tool_name,
                "input": last_tool_call.tool_input,
            })
            loop_messages.append({"role": "assistant", "content": assistant_content})
            loop_messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": last_tool_call.tool_use_id,
                    "content": json.dumps(tool_response, ensure_ascii=False),
                }],
            })
            continue

        break  # unknown tool

    # --- 专业 Agent 子循环（仅在 route_to_agent 触发时运行）---
    if last_tool_call and last_tool_call.tool_name == ROUTE_TO_AGENT_TOOL_NAME:
        routing_slug = last_tool_call.tool_input.get("agent", "")
        routing_reason = last_tool_call.tool_input.get("reason", "")
        specialist = SPECIALIST_AGENTS.get(routing_slug)

        yield sse("chat.tool_call", tool=ROUTE_TO_AGENT_TOOL_NAME, agent=routing_slug, reason=routing_reason)
        logger.info("routing_to_specialist", agent=routing_slug, reason=routing_reason)

        if specialist:
            # 把路由工具调用追加到共享上下文
            loop_messages.append({
                "role": "assistant",
                "content": [{
                    "type": "tool_use",
                    "id": last_tool_call.tool_use_id,
                    "name": ROUTE_TO_AGENT_TOOL_NAME,
                    "input": last_tool_call.tool_input,
                }],
            })
            loop_messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": last_tool_call.tool_use_id,
                    "content": f"已切换到{specialist.name}，请为用户提供专业服务。",
                }],
            })

            for _spec_iter in range(3):
                try:
                    spec_gen, spec_result = await client.stream_with_tools(
                        messages=loop_messages,
                        tools=SPECIALIST_TOOLS,  # type: ignore[arg-type]
                        system=specialist.system_prompt,
                        model=agent.model,
                        max_tokens=agent.max_tokens,
                    )
                    spec_iter_text = ""
                    async for chunk in spec_gen:
                        spec_iter_text += chunk
                        yield sse("chat.content_chunk", text=chunk)
                except ExternalServiceError as e:
                    yield sse("chat.error", message=str(e))
                    return

                full_text += spec_iter_text
                last_tool_call = spec_result.tool_call

                if not last_tool_call:
                    break

                if last_tool_call.tool_name == HANDOFF_TOOL_NAME:
                    break

                if last_tool_call.tool_name in QUERY_TOOL_NAMES:
                    yield sse("chat.tool_call", tool=last_tool_call.tool_name)
                    spec_response = await tools_service.execute_tool(
                        last_tool_call.tool_name, last_tool_call.tool_input
                    )
                    logger.info("specialist_tool_executed", tool=last_tool_call.tool_name, agent=routing_slug)

                    spec_content: list[dict[str, object]] = []
                    if spec_iter_text:
                        spec_content.append({"type": "text", "text": spec_iter_text})
                    spec_content.append({
                        "type": "tool_use",
                        "id": last_tool_call.tool_use_id,
                        "name": last_tool_call.tool_name,
                        "input": last_tool_call.tool_input,
                    })
                    loop_messages.append({"role": "assistant", "content": spec_content})
                    loop_messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": last_tool_call.tool_use_id,
                            "content": json.dumps(spec_response, ensure_ascii=False),
                        }],
                    })
                    continue

                break  # unknown tool in specialist

    # 保存 AI 全量回复
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
    if last_tool_call and last_tool_call.tool_name == HANDOFF_TOOL_NAME:
        tool_input = last_tool_call.tool_input
        reason: str = str(tool_input.get("reason", "AI 触发转人工"))
        summary: str = str(tool_input.get("summary", ""))

        logger.info("chat_handoff_triggered", conversation_id=str(conv.id), reason=reason)

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
            assigned_staff_id=(
                str(updated_conv.assigned_staff_id) if updated_conv.assigned_staff_id else None
            ),
        )
