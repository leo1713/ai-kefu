from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visitor import Visitor


async def get_or_create(db: AsyncSession, external_userid: str) -> Visitor:
    result = await db.execute(
        select(Visitor).where(
            Visitor.external_userid == external_userid,
            Visitor.deleted_at.is_(None),
        )
    )
    visitor = result.scalar_one_or_none()
    if not visitor:
        visitor = Visitor(external_userid=external_userid)
        db.add(visitor)
        await db.commit()
        await db.refresh(visitor)
    return visitor


async def list_all(
    db: AsyncSession,
    search: str | None = None,
    tag: str | None = None,
    limit: int = 50,
) -> list[Visitor]:
    stmt = (
        select(Visitor)
        .where(Visitor.deleted_at.is_(None))
        .order_by(Visitor.updated_at.desc())
        .limit(limit)
    )
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                Visitor.external_userid.ilike(pattern),
                Visitor.name.ilike(pattern),
            )
        )
    result = await db.execute(stmt)
    visitors = list(result.scalars().all())
    if tag:
        # JSON contains filter done in Python (portable across PG versions)
        visitors = [v for v in visitors if tag in (v.tags or [])]
    return visitors


async def update_visitor(
    db: AsyncSession,
    visitor_id: uuid.UUID,
    **kwargs: Any,
) -> Visitor:
    result = await db.execute(
        select(Visitor).where(Visitor.id == visitor_id, Visitor.deleted_at.is_(None))
    )
    visitor = result.scalar_one_or_none()
    if not visitor:
        from app.core.exceptions import NotFoundError
        raise NotFoundError(f"Visitor {visitor_id} not found")
    for key, value in kwargs.items():
        if value is not None or key in ("notes",):
            setattr(visitor, key, value)
    db.add(visitor)
    await db.commit()
    await db.refresh(visitor)
    return visitor
