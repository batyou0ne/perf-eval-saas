import logging
import uuid
from datetime import timedelta

import jwt
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.redis import redis_client
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_secure_token,
    hash_password,
    verify_password,
)
from app.crud.user import get_user_by_email, get_user_by_id
from app.models.user import User
from app.services import email_service

settings = get_settings()
logger = logging.getLogger(__name__)

REFRESH_KEY_PREFIX = "refresh_token:"
PASSWORD_RESET_KEY_PREFIX = "password_reset:"


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    user = await get_user_by_email(db, email)
    if user is None or not verify_password(password, user.hashed_password):
        logger.warning("Login attempt failed", extra={"email": email, "reason": "invalid_credentials"})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if not user.is_active:
        logger.warning("Login attempt failed", extra={"email": email, "reason": "inactive_account"})
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")
    return user


async def _store_refresh_token(jti: str, user_id: uuid.UUID) -> None:
    ttl = timedelta(days=settings.refresh_token_expire_days)
    await redis_client.set(f"{REFRESH_KEY_PREFIX}{jti}", str(user_id), ex=ttl)


async def issue_tokens(user: User, remember_me: bool = False) -> tuple[str, str]:
    access_token = create_access_token(str(user.id))
    refresh_token, jti = create_refresh_token(str(user.id), remember_me=remember_me)
    await _store_refresh_token(jti, user.id)
    return access_token, refresh_token


async def rotate_refresh_token(db: AsyncSession, refresh_token: str) -> tuple[str, str, bool]:
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
    remember_me = payload.get("remember_me", False)
    access_token, new_refresh_token = await issue_tokens(user, remember_me=remember_me)
    return access_token, new_refresh_token, remember_me


async def revoke_refresh_token(refresh_token: str) -> None:
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError:
        return

    jti = payload.get("jti")
    if jti:
        await redis_client.delete(f"{REFRESH_KEY_PREFIX}{jti}")


async def request_password_reset(db: AsyncSession, email: str) -> None:
    user = await get_user_by_email(db, email)
    if user is None:
        return  # don't reveal whether this email is registered

    token = generate_secure_token()
    ttl = timedelta(minutes=settings.password_reset_expire_minutes)
    await redis_client.set(f"{PASSWORD_RESET_KEY_PREFIX}{token}", str(user.id), ex=ttl)

    reset_link = f"{settings.frontend_url}/reset-password/{token}"
    email_service.send_password_reset_email(email, reset_link)


async def confirm_password_reset(db: AsyncSession, token: str, new_password: str) -> User:
    invalid = HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    redis_key = f"{PASSWORD_RESET_KEY_PREFIX}{token}"
    user_id = await redis_client.get(redis_key)
    if user_id is None:
        raise invalid

    user = await get_user_by_id(db, uuid.UUID(user_id))
    if user is None:
        raise invalid

    user.hashed_password = hash_password(new_password)
    await db.commit()
    await redis_client.delete(redis_key)
    return user
