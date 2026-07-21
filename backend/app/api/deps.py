import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.crud.user import get_user_by_id
from app.models.user import User, UserRole

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError:
        raise credentials_error

    if payload.get("type") != "access":
        raise credentials_error

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise credentials_error

    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise credentials_error

    return user


def require_role(*allowed_roles: UserRole):
    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        return current_user

    return dependency
