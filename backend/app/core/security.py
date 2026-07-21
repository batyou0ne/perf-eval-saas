import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings

settings = get_settings()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


def _create_token(subject: str, token_type: str, expires_delta: timedelta) -> tuple[str, str]:
    jti = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "jti": jti,
        "iat": now,
        "exp": now + expires_delta,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, jti


def create_access_token(user_id: str) -> str:
    token, _ = _create_token(user_id, "access", timedelta(minutes=settings.access_token_expire_minutes))
    return token


def create_refresh_token(user_id: str) -> tuple[str, str]:
    return _create_token(user_id, "refresh", timedelta(days=settings.refresh_token_expire_days))


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
