import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.models.evaluation import EvaluationStatus
from app.models.evaluation_cycle import CycleStatus
from app.models.question import QuestionType


class QuestionCreate(BaseModel):
    text: str
    type: QuestionType
    order: int = 0


class QuestionRead(BaseModel):
    id: uuid.UUID
    text: str
    type: QuestionType
    order: int

    model_config = {"from_attributes": True}


class CycleCreate(BaseModel):
    name: str
    start_date: date
    end_date: date
    questions: list[QuestionCreate]


class CycleUpdate(BaseModel):
    name: str
    start_date: date
    end_date: date
    questions: list[QuestionCreate]


class CycleRead(BaseModel):
    id: uuid.UUID
    name: str
    start_date: date
    end_date: date
    status: CycleStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class CycleDetail(CycleRead):
    questions: list[QuestionRead]


class SubjectProgress(BaseModel):
    subject_id: uuid.UUID
    subject_name: str
    self_status: EvaluationStatus
    # None means the subject has no manager, so no manager evaluation exists for them.
    manager_status: EvaluationStatus | None


class CycleProgress(BaseModel):
    self_submitted: int
    self_total: int
    manager_submitted: int
    manager_total: int
    subjects: list[SubjectProgress]
