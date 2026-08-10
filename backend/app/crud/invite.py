import uuid

from sqlalchemy import func, select
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


async def list_invites_by_company(
    db: AsyncSession, company_id: uuid.UUID, offset: int, limit: int
) -> tuple[list[Invite], int]:
    total = await db.scalar(select(func.count()).select_from(Invite).where(Invite.company_id == company_id))
    result = await db.execute(
        select(Invite)
        .where(Invite.company_id == company_id)
        .order_by(Invite.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), total or 0
