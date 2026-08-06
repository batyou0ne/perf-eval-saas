import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.invite import Invite


async def get_invite_by_token(db: AsyncSession, token: str) -> Invite | None:
    result = await db.execute(
        select(Invite).where(Invite.token == token).options(selectinload(Invite.company))
    )
    return result.scalar_one_or_none()


async def get_invite_by_id(db: AsyncSession, invite_id: uuid.UUID) -> Invite | None:
    result = await db.execute(
        select(Invite).where(Invite.id == invite_id).options(selectinload(Invite.company))
    )
    return result.scalar_one_or_none()


async def list_invites_by_company(db: AsyncSession, company_id: uuid.UUID) -> list[Invite]:
    result = await db.execute(
        select(Invite).where(Invite.company_id == company_id).order_by(Invite.created_at.desc())
    )
    return list(result.scalars().all())
