from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.cookies import REFRESH_COOKIE_NAME, clear_refresh_cookie, set_refresh_cookie
from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    TokenResponse,
    UserRead,
)
from app.services import auth_service

router = APIRouter()


@router.post("/auth/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request, body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    user = await auth_service.authenticate_user(db, body.email, body.password)
    access_token, refresh_token = await auth_service.issue_tokens(user, remember_me=body.remember_me)
    set_refresh_cookie(response, refresh_token, remember_me=body.remember_me)
    return TokenResponse(access_token=access_token)


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if refresh_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")

    access_token, new_refresh_token, remember_me = await auth_service.rotate_refresh_token(db, refresh_token)
    set_refresh_cookie(response, new_refresh_token, remember_me=remember_me)
    return TokenResponse(access_token=access_token)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response) -> None:
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if refresh_token:
        await auth_service.revoke_refresh_token(refresh_token)
    clear_refresh_cookie(response)


@router.get("/auth/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/auth/password-reset/request", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("3/minute")
async def request_password_reset(
    request: Request, body: PasswordResetRequest, db: AsyncSession = Depends(get_db)
) -> None:
    await auth_service.request_password_reset(db, body.email)


@router.post("/auth/password-reset/confirm", response_model=TokenResponse)
async def confirm_password_reset(
    body: PasswordResetConfirm, response: Response, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    user = await auth_service.confirm_password_reset(db, body.token, body.new_password)
    access_token, refresh_token = await auth_service.issue_tokens(user, remember_me=True)
    set_refresh_cookie(response, refresh_token, remember_me=True)
    return TokenResponse(access_token=access_token)
