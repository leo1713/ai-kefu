from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message


async def get_or_create_active(
    db: AsyncSession, visitor_id: uuid.UUID
) -> Conversation:
    result = await db.execute(
        select(Conversation)
        .where(
            Conversation.visitor_id == visitor_id,
            Conversation.status == "active",
            Conversation.deleted_at.is_(None),
        )
        .order_by(Conversation.created_at.desc())
    )
    conv = result.scalars().first()
    if not conv:
        conv = Conversation(visitor_id=visitor_id, status="active")
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
    return conv


async def get_recent_messages(
    db: AsyncSession, conversation_id: uuid.UUID, limit: int = 20
) -> list[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    msgs = list(result.scalars().all())
    msgs.reverse()
    return msgs
