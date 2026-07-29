from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.integrations.wecom.client import WeComClient
from app.integrations.wecom.crypto import WeComCrypto
from app.services.chat_service import chat_stream

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
    root = ET.fromstring(xml_str)
    return {child.tag: (child.text or "") for child in root}


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

    # Collect full AI response (non-streaming for WeCom)
    full_reply = ""
    async for sse_str in chat_stream(db, from_user, content):
        if '"event": "chat.content_chunk"' in sse_str:
            import json
            try:
                data_obj = json.loads(sse_str.replace("data: ", "").strip())
                full_reply += data_obj.get("text", "")
            except Exception:
                pass

    if full_reply:
        client = get_client()
        await client.send_text(
            to_user=from_user,
            agent_id=settings.wecom_agent_id,
            content=full_reply,
        )

    logger.info("wecom_message_handled", from_user=from_user, msg_id=msg_id)
