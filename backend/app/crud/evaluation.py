import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.evaluation import Evaluation
from app.models.evaluation_cycle import EvaluationCycle
from app.models.response import Response
from app.models.user import User


async def list_evaluations_for_user(db: AsyncSession, user_id: uuid.UUID) -> list[Evaluation]:
    result = await db.execute(
        select(Evaluation)
        .where(or_(Evaluation.evaluator_id == user_id, Evaluation.subject_id == user_id))
        .options(
            selectinload(Evaluation.cycle),
            selectinload(Evaluation.subject),
            selectinload(Evaluation.evaluator),
        )
        .order_by(Evaluation.created_at.desc())
    )
    return list(result.scalars().all())


_DETAIL_OPTIONS = (
    selectinload(Evaluation.cycle).selectinload(EvaluationCycle.questions),
    selectinload(Evaluation.subject),
    selectinload(Evaluation.evaluator),
    selectinload(Evaluation.responses).selectinload(Response.question),
)


async def get_evaluation_by_id(db: AsyncSession, evaluation_id: uuid.UUID) -> Evaluation | None:
    # populate_existing: without it, a second call within the same session (e.g. re-fetching
    # after submit_responses adds new Response rows) returns the same identity-mapped object
    # with its already-loaded (stale) `responses` collection from the first fetch, not the
    # freshly committed rows.
    result = await db.execute(
        select(Evaluation)
        .where(Evaluation.id == evaluation_id)
        .options(*_DETAIL_OPTIONS)
        .execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()


async def get_evaluations_for_subject_in_cycle(
    db: AsyncSession, cycle_id: uuid.UUID, subject_id: uuid.UUID
) -> list[Evaluation]:
    result = await db.execute(
        select(Evaluation)
        .where(Evaluation.cycle_id == cycle_id, Evaluation.subject_id == subject_id)
        .options(*_DETAIL_OPTIONS)
        .execution_options(populate_existing=True)
    )
    return list(result.scalars().all())


async def get_evaluations_for_cycle(db: AsyncSession, cycle_id: uuid.UUID) -> list[Evaluation]:
    """All self and manager evaluations for a cycle, ordered by subject name for stable grouping."""
    result = await db.execute(
        select(Evaluation)
        .where(Evaluation.cycle_id == cycle_id)
        .join(User, Evaluation.subject_id == User.id)
        .options(selectinload(Evaluation.subject))
        .order_by(User.full_name)
    )
    return list(result.scalars().all())
