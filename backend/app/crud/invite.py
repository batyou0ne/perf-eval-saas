from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.invite import Invite


async def get_invite_by_token(db: AsyncSession, token: str) -> Invite | None:
    result = await db.execute(
        select(Invite).where(Invite.token == token).options(selectinload(Invite.company))
    )
    return result.scalar_one_or_none()
