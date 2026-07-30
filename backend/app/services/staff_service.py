from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.models.staff import Staff
from app.schemas.staff import StaffCreate, StaffUpdate
from app.services.auth_service import hash_password


async def list_staff(
    db: AsyncSession,
    include_inactive: bool = False,
) -> list[Staff]:
    stmt = select(Staff).where(Staff.deleted_at.is_(None))
    if not include_inactive:
        stmt = stmt.where(Staff.is_active.is_(True))
    result = await db.execute(stmt.order_by(Staff.created_at))
    return list(result.scalars().all())


async def get_staff(db: AsyncSession, staff_id: uuid.UUID) -> Staff:
    result = await db.execute(
        select(Staff).where(Staff.id == staff_id, Staff.deleted_at.is_(None))
    )
    staff = result.scalar_one_or_none()
    if not staff:
        raise NotFoundError(f"Staff {staff_id} not found")
    return staff


async def create_staff(db: AsyncSession, data: StaffCreate) -> Staff:
    existing = await db.execute(select(Staff).where(Staff.username == data.username))
    if existing.scalar_one_or_none():
        raise ValidationError(f"用户名 '{data.username}' 已存在")
    staff = Staff(
        username=data.username,
        hashed_password=hash_password(data.password),
        display_name=data.display_name,
        wecom_userid=data.wecom_userid,
    )
    db.add(staff)
    await db.commit()
    await db.refresh(staff)
    return staff


async def update_staff(db: AsyncSession, staff_id: uuid.UUID, data: StaffUpdate) -> Staff:
    staff = await get_staff(db, staff_id)
    if data.display_name is not None:
        staff.display_name = data.display_name
    if data.wecom_userid is not None:
        staff.wecom_userid = data.wecom_userid
    if data.is_active is not None:
        staff.is_active = data.is_active
    db.add(staff)
    await db.commit()
    await db.refresh(staff)
    return staff
