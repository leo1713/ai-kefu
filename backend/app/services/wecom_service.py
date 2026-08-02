from __future__ import annotations

import json
from typing import Any

import defusedxml.ElementTree as ET
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.integrations.wecom.client import WeComClient
from app.integrations.wecom.crypto import WeComCrypto
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.staff import Staff
from app.services import visitor_service
from app.services.chat_service import chat_stream
from app.websocket.manager import manager

logger = structlog.get_logger()


def get_crypto() -> WeComCrypto:
    return WeComCrypto(
        token=settings.wecom_token,
        encoding_aes_key=settings.wecom_encoding_aes_key,
        corp_id=settings.wecom_corp_id,
    )


def get_client() -> WeComClient:
    return WeComClient(
        corp_id=settings.wecom_corp_id,
        secret=settings.wecom_secret,
    )


def parse_xml(xml_str: str) -> dict[str, Any]:
    """安全解析 XML，使用 defusedxml 防止 XML bomb 攻击。"""
    root = ET.fromstring(xml_str)
    return {child.tag: (child.text or "") for child in root}


async def notify_staff_handoff(
    client: WeComClient,
    staff_wecom_userid: str,
    visitor_external_userid: str,
    reason: str,
    summary: str = "",
) -> None:
    """通知客服有新的转人工会话。"""
    content = (
        f"【新转人工消息】\n"
        f"访客：{visitor_external_userid}\n"
        f"原因：{reason}\n"
    )
    if summary:
        content += f"对话摘要：{summary}\n"
    content += "\n请登录客服工作台接待该访客。"

    try:
        await client.send_text(
            to_user=staff_wecom_userid,
            agent_id=settings.wecom_agent_id,
            content=content,
        )
        logger.info(
            "wecom_staff_notified",
            staff_wecom_userid=staff_wecom_userid,
            visitor=visitor_external_userid,
        )
    except Exception as e:
        logger.warning("wecom_staff_notify_failed", error=str(e))


async def handle_message(db: AsyncSession, xml_body: str) -> None:
    data = parse_xml(xml_body)
    msg_type = data.get("MsgType", "")
    from_user = data.get("FromUserName", "")
    msg_id = data.get("MsgId", "")

    if msg_type == "text":
        content = data.get("Content", "").strip()
    elif msg_type == "image":
        content = "[图片消息，请描述您的问题]"
    else:
        logger.info("wecom_unsupported_msg_type", msg_type=msg_type)
        return

    if not content:
        return

    # 检查访客当前会话是否已转人工
    visitor = await visitor_service.get_or_create(db, from_user)
    result = await db.execute(
        select(Conversation)
        .where(
            Conversation.visitor_id == visitor.id,
            Conversation.deleted_at.is_(None),
        )
        .order_by(Conversation.updated_at.desc())
        .limit(1)
    )
    current_conv = result.scalar_one_or_none()

    if current_conv and current_conv.status == "transferred":
        # 会话已转人工：消息写入数据库，不 AI 回复，通知客服
        visitor_msg = Message(
            conversation_id=current_conv.id,
            role="user",
            content=content,
            msg_type="text",
        )
        db.add(visitor_msg)
        await db.commit()
        await db.refresh(visitor_msg)

        logger.info(
            "wecom_message_queued_for_staff",
            from_user=from_user,
            conversation_id=str(current_conv.id),
        )

        if current_conv.assigned_staff_id:
            await manager.send_to_staff(
                str(current_conv.assigned_staff_id),
                {
                    "event": "new_message",
                    "conversation_id": str(current_conv.id),
                    "message": {
                        "id": str(visitor_msg.id),
                        "role": visitor_msg.role,
                        "content": visitor_msg.content,
                        "msg_type": visitor_msg.msg_type,
                        "created_at": visitor_msg.created_at.isoformat(),
                    },
                },
            )

            # 推送企微通知给客服
            staff_result = await db.execute(
                select(Staff).where(Staff.id == current_conv.assigned_staff_id)
            )
            staff = staff_result.scalar_one_or_none()
            if staff and staff.wecom_userid:
                client = get_client()
                await notify_staff_handoff(
                    client=client,
                    staff_wecom_userid=staff.wecom_userid,
                    visitor_external_userid=from_user,
                    reason="访客在转人工会话中发送了新消息",
                )
        return

    # 正常 AI 回复流程，收集完整响应
    full_reply = ""
    handoff_triggered = False
    handoff_reason = ""
    handoff_summary = ""

    async for sse_str in chat_stream(db, from_user, content):
        if '"event": "chat.content_chunk"' in sse_str:
            try:
                raw = sse_str.replace("data: ", "").strip()
                data_obj = json.loads(raw)
                full_reply += data_obj.get("text", "")
            except Exception:
                pass
        elif '"event": "chat.handoff"' in sse_str:
            handoff_triggered = True
            try:
                raw = sse_str.replace("data: ", "").strip()
                data_obj = json.loads(raw)
                handoff_reason = data_obj.get("reason", "")
            except Exception:
                pass
        elif '"event": "chat.tool_call"' in sse_str:
            try:
                raw = sse_str.replace("data: ", "").strip()
                data_obj = json.loads(raw)
                handoff_summary = data_obj.get("summary", "")
            except Exception:
                pass

    wecom_client = get_client()

    if handoff_triggered:
        transfer_notice = full_reply or "您的问题已转接给人工客服，请稍候，客服人员将很快为您服务。"
        await wecom_client.send_text(
            to_user=from_user,
            agent_id=settings.wecom_agent_id,
            content=transfer_notice,
        )

        # 重新查询获取最新分配状态
        result2 = await db.execute(
            select(Conversation)
            .where(
                Conversation.visitor_id == visitor.id,
                Conversation.deleted_at.is_(None),
            )
            .order_by(Conversation.updated_at.desc())
            .limit(1)
        )
        updated_conv = result2.scalar_one_or_none()
        if updated_conv and updated_conv.assigned_staff_id:
            staff_result2 = await db.execute(
                select(Staff).where(Staff.id == updated_conv.assigned_staff_id)
            )
            staff2 = staff_result2.scalar_one_or_none()
            if staff2 and staff2.wecom_userid:
                await notify_staff_handoff(
                    client=wecom_client,
                    staff_wecom_userid=staff2.wecom_userid,
                    visitor_external_userid=from_user,
                    reason=handoff_reason,
                    summary=handoff_summary,
                )
            await manager.send_to_staff(
                str(updated_conv.assigned_staff_id),
                {
                    "event": "conversation_transferred",
                    "conversation": {
                        "id": str(updated_conv.id),
                        "visitor_id": str(updated_conv.visitor_id),
                        "visitor_external_userid": from_user,
                        "status": updated_conv.status,
                        "transfer_reason": updated_conv.transfer_reason,
                        "assigned_staff_id": str(updated_conv.assigned_staff_id),
                        "created_at": updated_conv.created_at.isoformat(),
                        "updated_at": updated_conv.updated_at.isoformat(),
                    },
                },
            )
    elif full_reply:
        await wecom_client.send_text(
            to_user=from_user,
            agent_id=settings.wecom_agent_id,
            content=full_reply,
        )

    logger.info("wecom_message_handled", from_user=from_user, msg_id=msg_id)
