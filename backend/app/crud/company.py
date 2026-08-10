from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company


async def list_companies(db: AsyncSession, offset: int, limit: int) -> tuple[list[Company], int]:
    total = await db.scalar(select(func.count()).select_from(Company))
    result = await db.execute(select(Company).order_by(Company.name).offset(offset).limit(limit))
    return list(result.scalars().all()), total or 0


async def list_all_companies(db: AsyncSession) -> list[Company]:
    """Deliberately unpaginated: this feeds a picker, which needs every option."""
    result = await db.execute(select(Company).order_by(Company.name))
    return list(result.scalars().all())
