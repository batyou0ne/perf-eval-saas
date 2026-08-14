import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.models.evaluation import EvaluationStatus, EvaluationType
from app.models.question import QuestionType
from app.schemas.evaluation_cycle import QuestionRead
from app.schemas.task import TaskEvidence


class EvaluationSummary(BaseModel):
    id: uuid.UUID
    cycle_id: uuid.UUID
    cycle_name: str
    cycle_end_date: date
    subject_id: uuid.UUID
    subject_name: str
    evaluator_id: uuid.UUID
    evaluator_name: str
    type: EvaluationType
    status: EvaluationStatus
    submitted_at: datetime | None


class ResponseInput(BaseModel):
    question_id: uuid.UUID
    rating_value: int | None = None
    text_value: str | None = None


class ResponseRead(BaseModel):
    question_id: uuid.UUID
    question_text: str
    question_type: QuestionType
    rating_value: int | None
    text_value: str | None


class EvaluationDetail(BaseModel):
    id: uuid.UUID
    cycle_id: uuid.UUID
    cycle_name: str
    subject_id: uuid.UUID
    subject_name: str
    evaluator_id: uuid.UUID
    evaluator_name: str
    type: EvaluationType
    status: EvaluationStatus
    submitted_at: datetime | None
    questions: list[QuestionRead]
    responses: list[ResponseRead]
    # Evidence, not input: the subject's completed tasks within the cycle's date range,
    # shown alongside the form so answers don't have to be written from memory alone.
    completed_tasks: list[TaskEvidence]


class EvaluationSubmit(BaseModel):
    responses: list[ResponseInput]


class EvaluationDraftSave(BaseModel):
    """Partial response list — unlike EvaluationSubmit, not every question needs to be present."""

    responses: list[ResponseInput]
