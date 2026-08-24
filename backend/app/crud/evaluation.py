import uuid
from collections.abc import Sequence

from sqlalchemy import Row, and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.evaluation import Evaluation, EvaluationStatus, EvaluationType
from app.models.evaluation_cycle import CycleStatus, EvaluationCycle
from app.models.response import Response
from app.models.user import User
from app.schemas.evaluation import ResponseInput


async def list_open_manager_evaluations_for_evaluator(
    db: AsyncSession, evaluator_id: uuid.UUID
) -> list[Evaluation]:
    """Manager evaluations this user still owes — what a handover has to move to someone else.

    Skips closed cycles: those can't be written to either way, so reassigning them would
    only hand the new evaluator work they're not allowed to do.
    """
    result = await db.execute(
        select(Evaluation)
        .join(EvaluationCycle, Evaluation.cycle_id == EvaluationCycle.id)
        .where(
            Evaluation.evaluator_id == evaluator_id,
            Evaluation.type == EvaluationType.MANAGER,
            Evaluation.status != EvaluationStatus.SUBMITTED,
            EvaluationCycle.status != CycleStatus.CLOSED,
        )
    )
    return list(result.scalars().all())


async def list_evaluations_for_user(
    db: AsyncSession, user_id: uuid.UUID, offset: int, limit: int, pending_only: bool = False
) -> tuple[list[Evaluation], int]:
    # pending_only narrows to "work this person still owes as evaluator" — a dashboard
    # widget's shape, distinct from the full self+subject listing the page normally shows.
    scope = (
        and_(Evaluation.evaluator_id == user_id, Evaluation.status != EvaluationStatus.SUBMITTED)
        if pending_only
        else or_(Evaluation.evaluator_id == user_id, Evaluation.subject_id == user_id)
    )

    total = await db.scalar(select(func.count()).select_from(Evaluation).where(scope))

    result = await db.execute(
        select(Evaluation)
        .where(scope)
        .options(
            selectinload(Evaluation.cycle),
            selectinload(Evaluation.subject),
            selectinload(Evaluation.evaluator),
        )
        .order_by(Evaluation.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), total or 0


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


def _submitted_of(evaluation_type: EvaluationType):
    """COUNT over a CASE that only yields a value for submitted rows of one type.

    COUNT ignores NULLs, so the implicit `else NULL` is what makes this a filtered
    count rather than a count of everything.
    """
    return func.count(
        case(
            (
                and_(
                    Evaluation.type == evaluation_type,
                    Evaluation.status == EvaluationStatus.SUBMITTED,
                ),
                1,
            )
        )
    )


def _total_of(evaluation_type: EvaluationType):
    return func.count(case((Evaluation.type == evaluation_type, 1)))


async def count_submissions_per_cycle(db: AsyncSession, company_id: uuid.UUID) -> list[Row]:
    """Per-cycle submitted/total counts for both evaluation types, oldest cycle first.

    One grouped query instead of walking every cycle and re-counting its evaluations,
    which is what the per-cycle progress endpoint does for a single cycle. The join is
    inner on purpose: a draft cycle that has never been activated has no evaluations,
    so it drops out here rather than showing up as an empty column on the chart.
    """
    result = await db.execute(
        select(
            EvaluationCycle.name,
            _submitted_of(EvaluationType.SELF).label("self_submitted"),
            _total_of(EvaluationType.SELF).label("self_total"),
            _submitted_of(EvaluationType.MANAGER).label("manager_submitted"),
            _total_of(EvaluationType.MANAGER).label("manager_total"),
        )
        .join(Evaluation, Evaluation.cycle_id == EvaluationCycle.id)
        .where(EvaluationCycle.company_id == company_id)
        .group_by(EvaluationCycle.id, EvaluationCycle.name, EvaluationCycle.start_date)
        # Name breaks ties so two cycles starting the same day keep a stable order
        # between requests, rather than the chart's bars swapping around.
        .order_by(EvaluationCycle.start_date, EvaluationCycle.name)
    )
    return list(result.all())


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
