import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def list_users_by_company(db: AsyncSession, company_id: uuid.UUID) -> list[User]:
    result = await db.execute(select(User).where(User.company_id == company_id).order_by(User.full_name))
    return list(result.scalars().all())


async def list_direct_reports(db: AsyncSession, manager_id: uuid.UUID) -> list[User]:
    result = await db.execute(select(User).where(User.manager_id == manager_id))
    return list(result.scalars().all())


async def list_active_users_by_company(db: AsyncSession, company_id: uuid.UUID) -> list[User]:
    result = await db.execute(
        select(User).where(User.company_id == company_id, User.is_active.is_(True))
    )
    return list(result.scalars().all())
