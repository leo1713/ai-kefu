from sqlalchemy import select
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
