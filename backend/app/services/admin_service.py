from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_str, encrypt_str
from app.models.settings import SystemSetting

_ANTHROPIC_KEY = "anthropic_api_key"


async def save_api_key(db: AsyncSession, key_name: str, api_key: str) -> None:
    encrypted = encrypt_str(api_key)
    existing = await db.get(SystemSetting, key_name)
    if existing:
        existing.encrypted_value = encrypted
    else:
        db.add(SystemSetting(key=key_name, encrypted_value=encrypted))
    await db.commit()


async def get_api_key(db: AsyncSession, key_name: str) -> str | None:
    setting = await db.get(SystemSetting, key_name)
    if not setting:
        return None
    return decrypt_str(setting.encrypted_value)


def mask_key(api_key: str) -> str:
    if len(api_key) <= 8:
        return "***"
    return f"{api_key[:4]}***{api_key[-4:]}"
