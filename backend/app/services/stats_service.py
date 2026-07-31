from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.visitor import Visitor


async def get_overview(db: AsyncSession) -> dict[str, object]:
    now = datetime.now(UTC)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)

    total_conv = await _count(db, Conversation, Conversation.deleted_at.is_(None))
    today_conv = await _count(
        db, Conversation,
        Conversation.deleted_at.is_(None),
        Conversation.created_at >= today,
    )
    week_conv = await _count(
        db, Conversation,
        Conversation.deleted_at.is_(None),
        Conversation.created_at >= week_ago,
    )
    transferred = await _count(
        db, Conversation,
        Conversation.deleted_at.is_(None),
        Conversation.status == "transferred",
    )
    total_msg = await _count(db, Message)
    total_visitors = await _count(db, Visitor, Visitor.deleted_at.is_(None))

    transfer_rate = round(transferred / total_conv * 100, 1) if total_conv else 0.0

    return {
        "total_conversations": total_conv,
        "today_conversations": today_conv,
        "week_conversations": week_conv,
        "transferred_conversations": transferred,
        "transfer_rate": transfer_rate,
        "total_messages": total_msg,
        "total_visitors": total_visitors,
    }


async def get_daily_stats(db: AsyncSession, days: int = 7) -> list[dict[str, object]]:
    today = date.today()
    result = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        start = datetime(d.year, d.month, d.day, tzinfo=UTC)
        end = start + timedelta(days=1)
        conv_count = await _count(
            db, Conversation,
            Conversation.deleted_at.is_(None),
            Conversation.created_at >= start,
            Conversation.created_at < end,
        )
        msg_count = await _count(
            db, Message,
            Message.created_at >= start,
            Message.created_at < end,
        )
        result.append({
            "date": d.isoformat(),
            "conversations": conv_count,
            "messages": msg_count,
        })
    return result


async def _count(db: AsyncSession, model: type, *filters: object) -> int:
    stmt = select(func.count()).select_from(model)
    for f in filters:
        stmt = stmt.where(f)  # type: ignore[arg-type]
    result = await db.execute(stmt)
    return result.scalar_one()
