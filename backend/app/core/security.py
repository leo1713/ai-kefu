import base64
import os
from datetime import UTC

from cryptography.fernet import Fernet


def _get_fernet() -> Fernet:
    from app.config import settings

    key = settings.encryption_key
    if not key:
        key = base64.urlsafe_b64encode(os.urandom(32)).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_str(value: str) -> str:
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt_str(token: str) -> str:
    return _get_fernet().decrypt(token.encode()).decode()


def create_access_token(data: dict[str, object]) -> str:
    from datetime import datetime, timedelta

    from jose import jwt

    from app.config import settings

    payload = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload["exp"] = expire
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, object]:
    from jose import jwt

    from app.config import settings

    return dict(jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm]))
