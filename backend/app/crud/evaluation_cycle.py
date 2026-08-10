import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.evaluation_cycle import EvaluationCycle


async def list_cycles_by_company(
    db: AsyncSession, company_id: uuid.UUID, offset: int, limit: int
) -> tuple[list[EvaluationCycle], int]:
    total = await db.scalar(
        select(func.count()).select_from(EvaluationCycle).where(EvaluationCycle.company_id == company_id)
    )
    result = await db.execute(
        select(EvaluationCycle)
        .where(EvaluationCycle.company_id == company_id)
        .order_by(EvaluationCycle.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), total or 0


async def get_cycle_by_id(db: AsyncSession, cycle_id: uuid.UUID) -> EvaluationCycle | None:
    result = await db.execute(
        select(EvaluationCycle)
        .where(EvaluationCycle.id == cycle_id)
        .options(selectinload(EvaluationCycle.questions))
    )
    return result.scalar_one_or_none()
