import uuid
from collections.abc import Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.evaluation import Evaluation
from app.models.evaluation_cycle import EvaluationCycle
from app.models.response import Response
from app.models.user import User
from app.schemas.evaluation import ResponseInput


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


async def upsert_responses(db: AsyncSession, evaluation_id: uuid.UUID, responses: Sequence[ResponseInput]) -> None:
    """Update existing (evaluation_id, question_id) rows in place, insert the rest.

    Keeps the unique constraint intact across repeated draft-saves and a later submit.
    Does not commit — the caller controls the transaction.
    """
    question_ids = [r.question_id for r in responses]
    result = await db.execute(
        select(Response).where(Response.evaluation_id == evaluation_id, Response.question_id.in_(question_ids))
    )
    existing_by_question_id = {r.question_id: r for r in result.scalars().all()}

    for response_input in responses:
        existing = existing_by_question_id.get(response_input.question_id)
        if existing is not None:
            existing.rating_value = response_input.rating_value
            existing.text_value = response_input.text_value
        else:
            db.add(
                Response(
                    evaluation_id=evaluation_id,
                    question_id=response_input.question_id,
                    rating_value=response_input.rating_value,
                    text_value=response_input.text_value,
                )
            )


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
