from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.visitor import Visitor


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


async def list_all(
    db: AsyncSession, limit: int = 50
) -> list[dict[str, object]]:
    stmt = (
        select(Conversation, Visitor.external_userid)
        .join(Visitor, Conversation.visitor_id == Visitor.id)
        .where(Conversation.deleted_at.is_(None))
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "id": str(row.Conversation.id),
            "visitor_id": str(row.Conversation.visitor_id),
            "visitor_external_userid": row.external_userid,
            "status": row.Conversation.status,
            "created_at": row.Conversation.created_at.isoformat(),
            "updated_at": row.Conversation.updated_at.isoformat(),
        }
        for row in rows
    ]


async def get_messages(
    db: AsyncSession, conversation_id: uuid.UUID
) -> list[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())

