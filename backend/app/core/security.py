from datetime import UTC

from cryptography.fernet import Fernet

_fernet_instance: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet_instance
    if _fernet_instance is not None:
        return _fernet_instance
    from app.config import settings
    from app.core.exceptions import AppException

    key = settings.encryption_key
    if not key:
        raise AppException(
            "ENCRYPTION_KEY 未配置。请在 .env 中设置 ENCRYPTION_KEY（Fernet base64 key）。"
            " 生成命令：python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    _fernet_instance = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet_instance


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
    from jose import JWTError, jwt

    from app.config import settings
    from app.core.exceptions import AuthenticationError

    try:
        return dict(jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm]))
    except JWTError as e:
        raise AuthenticationError("token 无效或已过期") from e
