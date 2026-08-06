import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.cookies import set_refresh_cookie
from app.api.deps import require_role
from app.core.config import get_settings
from app.core.database import get_db
from app.crud.invite import get_invite_by_token, list_invites_by_company
from app.models.user import User, UserRole
from app.schemas.auth import TokenResponse
from app.schemas.invite import InviteAccept, InviteCreate, InviteCreateResponse, InvitePreview, InviteRead
from app.services import auth_service, email_service, invite_service

router = APIRouter()
settings = get_settings()


def _build_invite_link(token: str) -> str:
    return f"{settings.frontend_url}/accept-invite/{token}"


@router.post("/invites", response_model=InviteCreateResponse)
async def create_invite(
    body: InviteCreate,
    db: AsyncSession = Depends(get_db),
    inviter: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN)),
) -> InviteCreateResponse:
    invite = await invite_service.create_invite(db, inviter, body)
    invite_link = _build_invite_link(invite.token)
    email_service.send_invite_email(invite.email, invite_link, invite.company.name)
    return InviteCreateResponse(
        email=invite.email, role=invite.role, invite_link=invite_link, expires_at=invite.expires_at
    )


@router.get("/invites", response_model=list[InviteRead])
async def list_invites(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COMPANY_ADMIN)),
) -> list[InviteRead]:
    return await list_invites_by_company(db, current_user.company_id)


@router.get("/invites/{token}", response_model=InvitePreview)
async def preview_invite(token: str, db: AsyncSession = Depends(get_db)) -> InvitePreview:
    invite = await get_invite_by_token(db, token)
    if invite is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invite not found")
    return InvitePreview(
        email=invite.email,
        role=invite.role,
        company_name=invite.company.name,
        expires_at=invite.expires_at,
        accepted_at=invite.accepted_at,
    )


@router.post("/invites/{token}/accept", response_model=TokenResponse)
async def accept_invite(
    token: str, body: InviteAccept, response: Response, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    invite = await get_invite_by_token(db, token)
    if invite is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invite not found")

    user = await invite_service.accept_invite(db, invite, body)
    access_token, refresh_token = await auth_service.issue_tokens(user, remember_me=True)
    set_refresh_cookie(response, refresh_token, remember_me=True)
    return TokenResponse(access_token=access_token)


@router.delete("/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_invite(
    invite_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COMPANY_ADMIN)),
) -> None:
    await invite_service.cancel_invite(db, current_user, invite_id)


@router.post("/invites/{invite_id}/resend", response_model=InviteCreateResponse)
async def resend_invite(
    invite_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COMPANY_ADMIN)),
) -> InviteCreateResponse:
    invite = await invite_service.resend_invite(db, current_user, invite_id)
    invite_link = _build_invite_link(invite.token)
    email_service.send_invite_email(invite.email, invite_link, invite.company.name)
    return InviteCreateResponse(
        email=invite.email, role=invite.role, invite_link=invite_link, expires_at=invite.expires_at
    )
