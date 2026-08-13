"""安全工具：JWT 签发/校验、密码哈希。
说明：使用 pbkdf2_sha256 而非 bcrypt，规避 passlib 与新版 bcrypt 的兼容性问题。
"""
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from core.config import settings

_pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _pwd.verify(plain, hashed)
    except Exception:
        return False


def get_password_hash(plain: str) -> str:
    return _pwd.hash(plain)


def create_access_token(subject: dict[str, Any], expires_minutes: int | None = None) -> str:
    expire = datetime.now(UTC) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode: dict[str, Any] = {**subject, "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str) -> dict[str, Any] | None:
    """校验 JWT，失败返回 None（供 core.deps 使用）。"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
