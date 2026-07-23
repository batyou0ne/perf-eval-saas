import uuid

from fastapi import HTTPException, status
from google.genai.errors import APIError, ClientError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.evaluation_summary import generate_evaluation_summary
from app.crud.evaluation import get_evaluations_for_subject_in_cycle
from app.crud.evaluation_summary import get_summary
from app.models.evaluation import Evaluation, EvaluationStatus, EvaluationType
from app.models.evaluation_summary import EvaluationSummary
from app.models.user import User
from app.schemas.evaluation_summary import EvaluationSummaryRead
from app.services.evaluation_service import can_view_evaluation


def _to_read(summary: EvaluationSummary) -> EvaluationSummaryRead:
    return EvaluationSummaryRead(
        id=summary.id,
        cycle_id=summary.cycle_id,
        subject_id=summary.subject_id,
        synthesis=summary.content["synthesis"],
        strengths=summary.content["strengths"],
        growth_areas=summary.content["growth_areas"],
        alignment_notes=summary.content["alignment_notes"],
        created_at=summary.created_at,
    )


def _qa_pairs(evaluation: Evaluation) -> list[tuple[str, str]]:
    pairs = []
    for r in evaluation.responses:
        answer = f"{r.rating_value} / 5" if r.rating_value is not None else (r.text_value or "")
        pairs.append((r.question.text, answer))
    return pairs


async def _authorize(db: AsyncSession, cycle_id: uuid.UUID, subject_id: uuid.UUID, current_user: User) -> list[Evaluation]:
    evaluations = await get_evaluations_for_subject_in_cycle(db, cycle_id, subject_id)
    if not evaluations or not any(can_view_evaluation(current_user, e) for e in evaluations):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to view this summary")
    return evaluations


async def get_summary_if_exists(
    db: AsyncSession, cycle_id: uuid.UUID, subject_id: uuid.UUID, current_user: User
) -> EvaluationSummaryRead:
    await _authorize(db, cycle_id, subject_id, current_user)

    existing = await get_summary(db, cycle_id, subject_id)
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No summary generated yet")
    return _to_read(existing)


async def get_or_generate_summary(
    db: AsyncSession, cycle_id: uuid.UUID, subject_id: uuid.UUID, current_user: User
) -> EvaluationSummaryRead:
    evaluations = await _authorize(db, cycle_id, subject_id, current_user)

    existing = await get_summary(db, cycle_id, subject_id)
    if existing is not None:
        return _to_read(existing)

    self_eval = next((e for e in evaluations if e.type == EvaluationType.SELF), None)
    manager_eval = next((e for e in evaluations if e.type == EvaluationType.MANAGER), None)

    if self_eval is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No self-evaluation exists for this cycle and person")
    if self_eval.status != EvaluationStatus.SUBMITTED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The self-evaluation must be submitted first")
    if manager_eval is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No manager evaluation exists for this cycle and person")
    if manager_eval.status != EvaluationStatus.SUBMITTED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The manager evaluation must be submitted first")

    try:
        content = await generate_evaluation_summary(
            subject_name=self_eval.subject.full_name,
            subject_role=self_eval.subject.role.value,
            cycle_name=self_eval.cycle.name,
            self_qa=_qa_pairs(self_eval),
            manager_name=manager_eval.evaluator.full_name,
            manager_qa=_qa_pairs(manager_eval),
        )
    except ClientError as exc:
        if exc.code == 429:
            detail = "The Gemini API free-tier quota was exceeded. Wait a bit and try again."
        elif exc.code in (401, 403):
            detail = "Gemini rejected the API key - check GEMINI_API_KEY in .env."
        else:
            detail = f"AI summary generation failed ({exc.code}). Please try again."
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail) from exc
    except APIError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "AI summary generation failed. Please try again.") from exc

    summary = EvaluationSummary(cycle_id=cycle_id, subject_id=subject_id, content=content.model_dump())
    db.add(summary)
    await db.commit()
    await db.refresh(summary)
    return _to_read(summary)
