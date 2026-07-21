import uuid
from datetime import timedelta

import jwt
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.redis import redis_client
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.crud.user import get_user_by_email, get_user_by_id
from app.models.user import User

settings = get_settings()

REFRESH_KEY_PREFIX = "refresh_token:"


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    user = await get_user_by_email(db, email)
    if user is None or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")
    return user


async def _store_refresh_token(jti: str, user_id: uuid.UUID) -> None:
    ttl = timedelta(days=settings.refresh_token_expire_days)
    await redis_client.setex(f"{REFRESH_KEY_PREFIX}{jti}", ttl, str(user_id))


async def issue_tokens(user: User) -> tuple[str, str]:
    access_token = create_access_token(str(user.id))
    refresh_token, jti = create_refresh_token(str(user.id))
    await _store_refresh_token(jti, user.id)
    return access_token, refresh_token


async def rotate_refresh_token(db: AsyncSession, refresh_token: str) -> tuple[str, str]:
    unauthorized = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError:
        raise unauthorized

    if payload.get("type") != "refresh":
        raise unauthorized

    redis_key = f"{REFRESH_KEY_PREFIX}{payload['jti']}"
    stored_user_id = await redis_client.get(redis_key)
    if stored_user_id is None or stored_user_id != payload["sub"]:
        raise unauthorized

    user = await get_user_by_id(db, uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise unauthorized

    await redis_client.delete(redis_key)
    return await issue_tokens(user)


async def revoke_refresh_token(refresh_token: str) -> None:
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError:
        return

    jti = payload.get("jti")
    if jti:
        await redis_client.delete(f"{REFRESH_KEY_PREFIX}{jti}")
