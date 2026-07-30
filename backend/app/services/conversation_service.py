from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.staff import Staff
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


async def transfer_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    reason: str,
    summary: str = "",
) -> Conversation:
    """将会话标记为 transferred，尝试自动分配空闲客服。"""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        from app.core.exceptions import NotFoundError
        raise NotFoundError(f"Conversation {conversation_id} not found")

    conv.status = "transferred"
    conv.transfer_reason = reason[:512] if reason else ""

    # 尝试自动分配：轮询找第一个活跃且尚未分配该会话的客服
    assigned = await _auto_assign_staff(db, conversation_id)
    if assigned:
        conv.assigned_staff_id = assigned.id

    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


async def assign_staff(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    staff_id: uuid.UUID,
) -> Conversation:
    """手动将会话分配给指定客服。"""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        from app.core.exceptions import NotFoundError
        raise NotFoundError(f"Conversation {conversation_id} not found")

    # 确认客服存在且活跃
    staff_result = await db.execute(
        select(Staff).where(Staff.id == staff_id, Staff.is_active.is_(True))
    )
    staff = staff_result.scalar_one_or_none()
    if not staff:
        from app.core.exceptions import NotFoundError
        raise NotFoundError(f"Staff {staff_id} not found or inactive")

    conv.assigned_staff_id = staff_id
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


async def _auto_assign_staff(
    db: AsyncSession, conversation_id: uuid.UUID
) -> Staff | None:
    """轮询分配：找当前活跃会话数最少的客服。"""
    result = await db.execute(
        select(Staff).where(
            Staff.is_active.is_(True),
            Staff.deleted_at.is_(None),
        )
    )
    staff_list = list(result.scalars().all())
    if not staff_list:
        return None

    # 统计每个客服当前的 transferred 会话数
    min_count = None
    chosen: Staff | None = None
    for staff in staff_list:
        count_result = await db.execute(
            select(Conversation).where(
                Conversation.assigned_staff_id == staff.id,
                Conversation.status == "transferred",
                Conversation.deleted_at.is_(None),
            )
        )
        count = len(list(count_result.scalars().all()))
        if min_count is None or count < min_count:
            min_count = count
            chosen = staff

    return chosen


async def close_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
) -> Conversation:
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        from app.core.exceptions import NotFoundError
        raise NotFoundError(f"Conversation {conversation_id} not found")
    conv.status = "closed"
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


async def reply_message(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    content: str,
) -> tuple[Message, str]:
    """保存客服回复，返回 (message, visitor_external_userid)。"""
    from app.core.exceptions import NotFoundError
    row = (await db.execute(
        select(Conversation, Visitor.external_userid)
        .join(Visitor, Conversation.visitor_id == Visitor.id)
        .where(Conversation.id == conversation_id, Conversation.deleted_at.is_(None))
    )).one_or_none()
    if not row:
        raise NotFoundError(f"Conversation {conversation_id} not found")
    _, external_userid = row
    msg = Message(
        conversation_id=conversation_id,
        role="staff",
        content=content,
        msg_type="text",
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg, str(external_userid)


async def list_all(
    db: AsyncSession,
    limit: int = 50,
    status: str | None = None,
    assigned_staff_id: uuid.UUID | None = None,
) -> list[dict[str, object]]:
    stmt = (
        select(Conversation, Visitor.external_userid)
        .join(Visitor, Conversation.visitor_id == Visitor.id)
        .where(Conversation.deleted_at.is_(None))
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
    )
    if status:
        stmt = stmt.where(Conversation.status == status)
    rows = (await db.execute(stmt)).all()
    return [
        {
            "id": str(row.Conversation.id),
            "visitor_id": str(row.Conversation.visitor_id),
            "visitor_external_userid": row.external_userid,
            "status": row.Conversation.status,
            "assigned_staff_id": (
                str(row.Conversation.assigned_staff_id)
                if row.Conversation.assigned_staff_id
                else None
            ),
            "transfer_reason": row.Conversation.transfer_reason,
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
