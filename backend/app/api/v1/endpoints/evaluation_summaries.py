import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.evaluation_summary import EvaluationSummaryRead
from app.services import evaluation_summary_service

router = APIRouter()


@router.post("/cycles/{cycle_id}/subjects/{subject_id}/summary", response_model=EvaluationSummaryRead)
async def generate_summary(
    cycle_id: uuid.UUID,
    subject_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EvaluationSummaryRead:
    return await evaluation_summary_service.get_or_generate_summary(db, cycle_id, subject_id, current_user)


@router.get("/cycles/{cycle_id}/subjects/{subject_id}/summary", response_model=EvaluationSummaryRead)
async def get_summary(
    cycle_id: uuid.UUID,
    subject_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EvaluationSummaryRead:
    return await evaluation_summary_service.get_summary_if_exists(db, cycle_id, subject_id, current_user)
