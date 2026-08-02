from __future__ import annotations

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError
from app.core.security import create_access_token
from app.models.staff import Staff


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


async def login(db: AsyncSession, username: str, password: str) -> str:
    result = await db.execute(
        select(Staff).where(Staff.username == username, Staff.is_active.is_(True))
    )
    staff = result.scalar_one_or_none()
    if not staff or not verify_password(password, staff.hashed_password):
        raise AuthenticationError("用户名或密码错误")
    return create_access_token({"sub": str(staff.id), "username": staff.username})


async def seed_default_admin(db: AsyncSession) -> Staff:
    from app.config import settings
    from app.core.exceptions import PermissionError, ValidationError

    if not settings.allow_init_admin:
        raise PermissionError("init-admin 未启用，请在 .env 中设置 ALLOW_INIT_ADMIN=true")
    if not settings.default_admin_password:
        raise ValidationError("DEFAULT_ADMIN_PASSWORD 未配置，请在 .env 中设置初始密码")

    result = await db.execute(select(Staff).where(Staff.username == "admin"))
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    admin = Staff(
        username="admin",
        hashed_password=hash_password(settings.default_admin_password),
        display_name="管理员",
    )
    db.add(admin)
    await db.commit()
    await db.refresh(admin)
    return admin
