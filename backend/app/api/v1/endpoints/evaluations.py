import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.evaluation import EvaluationDetail, EvaluationDraftSave, EvaluationSubmit, EvaluationSummary
from app.schemas.pagination import Page
from app.services import evaluation_service

router = APIRouter()


@router.get("/evaluations/me", response_model=Page[EvaluationSummary])
async def list_my_evaluations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    pending: bool = Query(default=False, description="Only evaluations this user still owes as evaluator"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Page[EvaluationSummary]:
    return await evaluation_service.list_my_evaluations(db, current_user, page, page_size, pending_only=pending)


@router.get("/evaluations/{evaluation_id}", response_model=EvaluationDetail)
async def get_evaluation(
    evaluation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EvaluationDetail:
    return await evaluation_service.get_evaluation_detail(db, evaluation_id, current_user)


@router.patch("/evaluations/{evaluation_id}", response_model=EvaluationDetail)
async def save_evaluation_draft(
    evaluation_id: uuid.UUID,
    body: EvaluationDraftSave,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EvaluationDetail:
    return await evaluation_service.save_draft(db, evaluation_id, current_user, body)


@router.post("/evaluations/{evaluation_id}/submit", response_model=EvaluationDetail)
async def submit_evaluation(
    evaluation_id: uuid.UUID,
    body: EvaluationSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EvaluationDetail:
    return await evaluation_service.submit_responses(db, evaluation_id, current_user, body)
