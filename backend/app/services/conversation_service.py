from __future__ import annotations

import uuid

from sqlalchemy import func, select
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
    """轮询分配：找当前 transferred 会话数最少的活跃客服（单次 GROUP BY 查询）。"""
    # 先取所有活跃客服 ID
    staff_result = await db.execute(
        select(Staff.id).where(
            Staff.is_active.is_(True),
            Staff.deleted_at.is_(None),
        )
    )
    staff_ids = [row[0] for row in staff_result.all()]
    if not staff_ids:
        return None

    # 一次查询统计每位客服当前 transferred 会话数
    count_col = func.count(Conversation.id).label("conv_count")
    count_result = await db.execute(
        select(Conversation.assigned_staff_id, count_col)
        .where(
            Conversation.assigned_staff_id.in_(staff_ids),
            Conversation.status == "transferred",
            Conversation.deleted_at.is_(None),
        )
        .group_by(Conversation.assigned_staff_id)
    )
    load_map: dict[uuid.UUID, int] = {row[0]: row[1] for row in count_result.all()}

    # 选负载最小的客服（没有分配记录的视为 0）
    chosen_id = min(staff_ids, key=lambda sid: load_map.get(sid, 0))

    chosen_result = await db.execute(select(Staff).where(Staff.id == chosen_id))
    return chosen_result.scalar_one_or_none()


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


async def reply_and_send_wecom(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    content: str,
) -> Message:
    """
    保存客服回复，并尝试通过企业微信将消息发送给访客。

    企微发送失败时记录 warning 但不影响主流程（消息已写库）。
    """
    import structlog as _structlog

    _logger = _structlog.get_logger()

    msg, visitor_external_userid = await reply_message(db, conversation_id, content)
    try:
        from app.config import settings as cfg
        from app.services.wecom_service import get_client

        client = get_client()
        await client.send_text(
            to_user=visitor_external_userid,
            agent_id=cfg.wecom_agent_id,
            content=content,
        )
    except Exception as e:
        _logger.warning(
            "wecom_reply_failed",
            conversation_id=str(conversation_id),
            error=str(e),
        )
    return msg


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
