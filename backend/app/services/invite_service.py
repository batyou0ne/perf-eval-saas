from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import generate_secure_token, hash_password
from app.crud.user import get_user_by_email
from app.models.company import Company
from app.models.invite import Invite
from app.models.user import User, UserRole
from app.schemas.invite import InviteAccept, InviteCreate

settings = get_settings()

INVITABLE_BY_SUPER_ADMIN = {UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN}
INVITABLE_BY_COMPANY_ADMIN = {UserRole.COMPANY_ADMIN, UserRole.MANAGER, UserRole.HR, UserRole.EMPLOYEE}


async def create_invite(db: AsyncSession, inviter: User, data: InviteCreate) -> Invite:
    if inviter.role == UserRole.SUPER_ADMIN:
        if data.company_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "company_id is required")
        if data.role not in INVITABLE_BY_SUPER_ADMIN:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Super admins can only invite company admins or other super admins")
        company_id = data.company_id
    elif inviter.role == UserRole.COMPANY_ADMIN:
        if data.role not in INVITABLE_BY_COMPANY_ADMIN:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot invite a super admin")
        company_id = inviter.company_id
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to invite users")

    company = await db.get(Company, company_id)
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")

    existing_user = await get_user_by_email(db, data.email)
    if existing_user is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A user with this email already exists")

    invite = Invite(
        email=data.email,
        company_id=company_id,
        role=data.role,
        token=generate_secure_token(),
        invited_by_id=inviter.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.invite_expire_days),
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)
    return invite


async def accept_invite(db: AsyncSession, invite: Invite, data: InviteAccept) -> User:
    if invite.accepted_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invite already accepted")
    if invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invite has expired")

    existing_user = await get_user_by_email(db, invite.email)
    if existing_user is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "An account with this email already exists")

    user = User(
        company_id=invite.company_id,
        email=invite.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=invite.role,
    )
    db.add(user)
    invite.accepted_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)
    return user
