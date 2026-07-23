import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.evaluation_cycle import EvaluationCycle


async def list_cycles_by_company(db: AsyncSession, company_id: uuid.UUID) -> list[EvaluationCycle]:
    result = await db.execute(
        select(EvaluationCycle)
        .where(EvaluationCycle.company_id == company_id)
        .order_by(EvaluationCycle.created_at.desc())
    )
    return list(result.scalars().all())


async def get_cycle_by_id(db: AsyncSession, cycle_id: uuid.UUID) -> EvaluationCycle | None:
    result = await db.execute(
        select(EvaluationCycle)
        .where(EvaluationCycle.id == cycle_id)
        .options(selectinload(EvaluationCycle.questions))
    )
    return result.scalar_one_or_none()
