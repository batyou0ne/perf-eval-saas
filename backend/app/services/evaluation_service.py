import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.evaluation import get_evaluation_by_id, list_evaluations_for_user
from app.models.evaluation import Evaluation, EvaluationStatus
from app.models.question import QuestionType
from app.models.response import Response
from app.models.user import User, UserRole
from app.schemas.evaluation import EvaluationDetail, EvaluationSubmit, EvaluationSummary, ResponseRead
from app.schemas.evaluation_cycle import QuestionRead


def can_view_evaluation(current_user: User, evaluation: Evaluation) -> bool:
    """Shared visibility rule, also used by the AI summary service."""
    if current_user.id == evaluation.evaluator_id:
        return True
    if current_user.id == evaluation.subject_id:
        return evaluation.status == EvaluationStatus.SUBMITTED
    is_company_oversight = current_user.role in (UserRole.COMPANY_ADMIN, UserRole.HR) and (
        current_user.company_id == evaluation.cycle.company_id
    )
    if is_company_oversight:
        return evaluation.status == EvaluationStatus.SUBMITTED
    return False


def _to_detail(evaluation: Evaluation) -> EvaluationDetail:
    return EvaluationDetail(
        id=evaluation.id,
        cycle_id=evaluation.cycle_id,
        cycle_name=evaluation.cycle.name,
        subject_id=evaluation.subject_id,
        subject_name=evaluation.subject.full_name,
        evaluator_id=evaluation.evaluator_id,
        evaluator_name=evaluation.evaluator.full_name,
        type=evaluation.type,
        status=evaluation.status,
        submitted_at=evaluation.submitted_at,
        questions=[QuestionRead.model_validate(q) for q in evaluation.cycle.questions],
        responses=[
            ResponseRead(
                question_id=r.question_id,
                question_text=r.question.text,
                question_type=r.question.type,
                rating_value=r.rating_value,
                text_value=r.text_value,
            )
            for r in evaluation.responses
        ],
    )


async def list_my_evaluations(db: AsyncSession, user: User) -> list[EvaluationSummary]:
    evaluations = await list_evaluations_for_user(db, user.id)
    return [
        EvaluationSummary(
            id=e.id,
            cycle_id=e.cycle_id,
            cycle_name=e.cycle.name,
            subject_id=e.subject_id,
            subject_name=e.subject.full_name,
            type=e.type,
            status=e.status,
            submitted_at=e.submitted_at,
        )
        for e in evaluations
    ]


async def get_evaluation_detail(db: AsyncSession, evaluation_id: uuid.UUID, current_user: User) -> EvaluationDetail:
    evaluation = await get_evaluation_by_id(db, evaluation_id)
    if evaluation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evaluation not found")

    if not can_view_evaluation(current_user, evaluation):
        detail = (
            "This evaluation hasn't been submitted yet"
            if current_user.id == evaluation.subject_id
            else "Not authorized to view this evaluation"
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail)

    return _to_detail(evaluation)


async def submit_responses(
    db: AsyncSession, evaluation_id: uuid.UUID, current_user: User, data: EvaluationSubmit
) -> EvaluationDetail:
    evaluation = await get_evaluation_by_id(db, evaluation_id)
    if evaluation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evaluation not found")

    if evaluation.evaluator_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the assigned evaluator can submit this evaluation")

    if evaluation.status == EvaluationStatus.SUBMITTED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This evaluation has already been submitted")

    questions_by_id = {q.id: q for q in evaluation.cycle.questions}
    submitted_question_ids = {r.question_id for r in data.responses}
    if submitted_question_ids != set(questions_by_id.keys()):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "All questions must be answered")

    for response_input in data.responses:
        question = questions_by_id[response_input.question_id]

        if question.type == QuestionType.RATING:
            if response_input.rating_value is None or not (1 <= response_input.rating_value <= 5):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"'{question.text}' requires a rating from 1 to 5")
        else:
            if not response_input.text_value:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"'{question.text}' requires a text answer")

        db.add(
            Response(
                evaluation_id=evaluation.id,
                question_id=response_input.question_id,
                rating_value=response_input.rating_value,
                text_value=response_input.text_value,
            )
        )

    evaluation.status = EvaluationStatus.SUBMITTED
    evaluation.submitted_at = datetime.now(timezone.utc)
    await db.commit()

    return _to_detail(await get_evaluation_by_id(db, evaluation.id))
