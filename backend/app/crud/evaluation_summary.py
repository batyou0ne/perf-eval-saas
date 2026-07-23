import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluation_summary import EvaluationSummary


async def get_summary(db: AsyncSession, cycle_id: uuid.UUID, subject_id: uuid.UUID) -> EvaluationSummary | None:
    result = await db.execute(
        select(EvaluationSummary).where(
            EvaluationSummary.cycle_id == cycle_id, EvaluationSummary.subject_id == subject_id
        )
    )
    return result.scalar_one_or_none()
